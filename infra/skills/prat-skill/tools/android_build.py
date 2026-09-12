#!/usr/bin/env python
"""android_build.py - build, inspect and install Android apps from Claude Code on Windows.

WHY THIS EXISTS
---------------
Gradle cannot run inside the Claude Code shell on this PC. Every build dies with

    java.io.IOException: Unable to establish loopback connection

Traced 15-Aug-2026 to the JDK: Selector.open() -> PipeImpl -> UnixDomainSockets.connect0
returns "Invalid argument: connect". AF_UNIX bind succeeds, connect fails. JDK 17 and 21
are all affected; JDK 11 is not. Plain TCP loopback works cross-process, so the machine's
networking is fine - it is the shell's process tree. --no-daemon, preferIPv4Stack, a short
java.io.tmpdir and disabling the sandbox all make no difference.

The workaround that DOES work: run Gradle from a Windows scheduled task, i.e. outside the
shell's process tree. This script wraps that so a build is one command again.

USAGE
-----
  python android_build.py build <project-dir> [--task :app:bundleRelease] [--tail 25]
  python android_build.py inspect <file.aab|file.apk>
  python android_build.py apks <file.aab> [--out out.apks] [--universal]
  python android_build.py install <file.aab|file.apks>      # needs a phone on adb

`inspect` is the step that matters most: a green build proves nothing about what is
actually inside the artifact. It prints versionCode, permissions and services read from
the built file itself - which is how the missing location permission was caught.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

SDK = Path.home() / "AppData/Local/Android/Sdk"
BUNDLETOOL = next(iter(sorted((SDK / "bundletool").glob("bundletool-all-*.jar"), reverse=True)), None)
TASK_NAME = "ClaudeAndroidBuild"
POLL_SECONDS = 5
BUILD_TIMEOUT_SECONDS = 1800


def find_jdk(minimum: int = 17) -> Path:
    """Pick a JDK deterministically: the LOWEST standalone JDK at or above `minimum`.

    AGP 8.x needs 17+, and 17 is what signed the accepted Alpha Nexus builds - so the
    same source must keep producing the same artifact rather than silently jumping to
    whatever newest JDK happens to be installed. Android Studio's bundled JBR is a last
    resort: it moves with the IDE, so it is not a stable build input.
    """
    roots = [Path("C:/Program Files/Eclipse Adoptium"), Path("C:/Program Files/Microsoft"),
             Path("C:/Program Files/Android/Android Studio")]
    found: list[tuple[int, int, Path]] = []
    for root in roots:
        if not root.exists():
            continue
        for d in root.iterdir():
            if not (d / "bin/java.exe").exists():
                continue
            m = re.search(r"jdk-(\d+)", d.name)
            is_jbr = d.name == "jbr"
            major = int(m.group(1)) if m else 21 if is_jbr else 0
            if major >= minimum:
                found.append((1 if is_jbr else 0, major, d))
    if not found:
        sys.exit(f"no JDK {minimum}+ found under {[str(r) for r in roots]}")
    return min(found)[2]


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace")


def build(project: Path, task: str, tail: int) -> int:
    gradlew = project / "gradlew.bat"
    if not gradlew.exists():
        sys.exit(f"no gradlew.bat in {project}")

    jdk, log = find_jdk(), project / "claude-build.log"
    bat = project / "claude-build.bat"
    # ANDROID_HOME is not inherited by the scheduled task: without it Gradle fails with
    # "SDK location not found" even though the SDK is installed.
    bat.write_text(
        "@echo off\r\n"
        f'set JAVA_HOME={jdk}\r\n'
        f"set ANDROID_HOME={SDK}\r\n"
        f'cd /d "{project}"\r\n'
        f'call gradlew.bat {task} --console=plain > "{log}" 2>&1\r\n'
        f'echo EXITCODE=%ERRORLEVEL% >> "{log}"\r\n',
        encoding="ascii",
    )
    log.unlink(missing_ok=True)

    print(f"jdk    {jdk.name}\nsdk    {SDK}\ntask   {task}\nin     {project}", flush=True)
    run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    created = run(["schtasks", "/Create", "/TN", TASK_NAME, "/TR", str(bat), "/SC", "ONCE", "/ST", "23:59", "/F"])
    if created.returncode:
        sys.exit(f"could not register the build task: {created.stdout}{created.stderr}")
    # A scheduled task will NOT start on battery power under Windows' defaults - it sits
    # in "Queued" forever with no log and no error. Burned 15-Aug-2026 when the laptop was
    # unplugged. schtasks cannot set this, so patch the settings through PowerShell.
    run(["powershell", "-NonInteractive", "-Command",
         f"Set-ScheduledTask -TaskName '{TASK_NAME}' -Settings (New-ScheduledTaskSettingsSet "
         f"-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
         f"-ExecutionTimeLimit (New-TimeSpan -Seconds {BUILD_TIMEOUT_SECONDS})) | Out-Null"])
    run(["schtasks", "/Run", "/TN", TASK_NAME])

    deadline = time.time() + BUILD_TIMEOUT_SECONDS
    while time.time() < deadline:
        if log.exists() and "EXITCODE=" in log.read_text(encoding="utf-8", errors="replace"):
            break
        time.sleep(POLL_SECONDS)
    else:
        run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
        sys.exit(f"build did not finish within {BUILD_TIMEOUT_SECONDS}s - see {log}")

    run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    text = log.read_text(encoding="utf-8", errors="replace")
    code = int(re.search(r"EXITCODE=(\d+)", text).group(1))
    print("\n".join(text.splitlines()[-tail:]))
    if code == 0:
        for art in sorted(project.rglob("build/outputs/**/*.a[ap][bk]*")):
            if art.suffix in (".aab", ".apk"):
                print(f"artifact  {art}  ({art.stat().st_size:,} bytes)")
    print(f"\nexit {code}  (full log: {log})")
    return code


def build_tools() -> Path:
    """Newest installed build-tools directory (holds aapt2 and apksigner)."""
    versions = sorted((SDK / "build-tools").glob("*"), key=lambda p: [int(x) for x in re.findall(r"\d+", p.name)])
    if not versions:
        sys.exit(f"no build-tools under {SDK / 'build-tools'}")
    return versions[-1]


def inspect(artifact: Path) -> int:
    """Read the BUILT file, not the source. A green build is not evidence.

    An .aab keeps its manifest as protobuf with plain UTF-8 strings, so it can be read
    straight out of the zip. An .apk does NOT: its manifest is compiled binary AXML with a
    UTF-16 string pool, and a v2/v3-signed APK has no META-INF/*.RSA at all. Reading an APK
    the same way as an AAB reports "UNSIGNED / permissions NONE" for a perfectly good file -
    a false negative that would condemn a working build. APKs therefore go through the SDK's
    own aapt2 and apksigner. (Caught 15-Aug-2026 on the first APK this tool ever inspected.)
    """
    if not artifact.exists():
        sys.exit(f"no such file: {artifact}")

    print(f"file        {artifact}  ({artifact.stat().st_size:,} bytes)")

    if artifact.suffix == ".apk":
        bt = build_tools()
        badging = run([str(bt / "aapt2.exe"), "dump", "badging", str(artifact)]).stdout
        certs = run([str(bt / "apksigner.bat"), "verify", "--print-certs", str(artifact)]).stdout
        pkg = next((ln for ln in badging.splitlines() if ln.startswith("package:")), "package: ?")
        perms = sorted({ln.split("'")[1] for ln in badging.splitlines() if ln.startswith("uses-permission:")})
        label = next((ln.split("'")[1] for ln in badging.splitlines() if ln.startswith("application-label:")), "?")
        signer = next((ln.split("DN: ")[1] for ln in certs.splitlines() if "certificate DN:" in ln), "UNSIGNED")
        print(f"{pkg}\nlabel       {label}\nsigned by   {signer}\npermissions {perms or 'NONE'}")
        return 0

    with zipfile.ZipFile(artifact) as z:
        manifest = z.read("base/manifest/AndroidManifest.xml")
        signed = [n for n in z.namelist() if n.startswith("META-INF") and n.endswith((".RSA", ".DSA", ".EC"))]
        resources = z.read("base/resources.pb")

    def strings(blob: bytes, pattern: str) -> list[str]:
        return sorted({m.decode() for m in re.findall(pattern.encode(), blob)})

    print(f"signed by   {signed or 'UNSIGNED (an AAB is signed jar-style; empty here is a real problem)'}")
    print(f"permissions {strings(manifest, r'android\.permission\.[A-Z_]+') or 'NONE'}")
    print(f"services    {strings(manifest, r'[a-z][a-zA-Z0-9_.]+Service') or 'none'}")
    print(f"urls        {strings(resources, r'https://[a-zA-Z0-9./_-]+')[:5] or 'none'}")
    return 0


def apks(aab: Path, out: Path | None, universal: bool) -> int:
    if BUNDLETOOL is None:
        sys.exit(f"bundletool not found under {SDK / 'bundletool'}")
    out = out or aab.with_suffix(".apks")
    cmd = [str(find_jdk() / "bin/java.exe"), "-jar", str(BUNDLETOOL), "build-apks",
           f"--bundle={aab}", f"--output={out}", "--overwrite"]
    if universal:
        cmd.append("--mode=universal")
    r = run(cmd)
    print(r.stdout or r.stderr)
    if r.returncode == 0:
        print(f"wrote {out} ({out.stat().st_size:,} bytes)")
    return r.returncode


def install(artifact: Path) -> int:
    adb = SDK / "platform-tools/adb.exe"
    devices = [ln for ln in run([str(adb), "devices"]).stdout.splitlines()[1:] if "\tdevice" in ln]
    if not devices:
        sys.exit("no phone on adb - plug one in with USB debugging on, then retry")
    target = artifact
    if artifact.suffix == ".aab":
        target = artifact.with_suffix(".apks")
        if apks(artifact, target, universal=False):
            return 1
    if BUNDLETOOL is None:
        sys.exit("bundletool not found")
    r = run([str(find_jdk() / "bin/java.exe"), "-jar", str(BUNDLETOOL), "install-apks", f"--apks={target}"])
    print(r.stdout or r.stderr)
    return r.returncode


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="run a gradle task outside the shell's process tree")
    b.add_argument("project", type=Path)
    b.add_argument("--task", default=":app:bundleRelease")
    b.add_argument("--tail", type=int, default=25)

    i = sub.add_parser("inspect", help="read permissions/services/urls out of a built aab or apk")
    i.add_argument("artifact", type=Path)

    a = sub.add_parser("apks", help="turn an aab into installable apks")
    a.add_argument("aab", type=Path)
    a.add_argument("--out", type=Path)
    a.add_argument("--universal", action="store_true")

    n = sub.add_parser("install", help="install an aab/apks onto a connected phone")
    n.add_argument("artifact", type=Path)

    args = p.parse_args()
    if args.cmd == "build":
        return build(args.project.resolve(), args.task, args.tail)
    if args.cmd == "inspect":
        return inspect(args.artifact.resolve())
    if args.cmd == "apks":
        return apks(args.aab.resolve(), args.out, args.universal)
    return install(args.artifact.resolve())


if __name__ == "__main__":
    sys.exit(main())
