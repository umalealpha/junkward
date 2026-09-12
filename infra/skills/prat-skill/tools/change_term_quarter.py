#!/usr/bin/env python3
"""Change a Graphite policy's term to a calendar quarter (Q1-Q4).

Quarters:
  Q1 = 01 Jan - 31 Mar      Q2 = 01 Apr - 30 Jun
  Q3 = 01 Jul - 30 Sep      Q4 = 01 Oct - 31 Dec

Changes ONLY the term period (policy_term.term_start_date / term_end_date) for
the policy's latest term (or a given --term-id). The premiums are unaffected:
coverages key on the term ID, not the dates.

Safety (prat-test): defaults to PREVIEW (no write). With --commit it runs the
update inside a transaction, re-reads the row, and only commits if the dates
verify; otherwise it rolls back. Backend reached via ECS exec into the prod
Graphite container (AWS profile `claude-cli`, Session Manager plugin).

USAGE:
  python change_term_quarter.py --policy COMG2024129498 --quarter 2 --year 2026
  python change_term_quarter.py --policy COMG2024129498 --quarter 2 --year 2026 --commit
  python change_term_quarter.py --term-id 8447 --quarter 2 --year 2026 --commit
"""
import argparse, base64, json, os, re, subprocess, sys

PLUGIN_DIR = r"C:\Program Files\Amazon\SessionManagerPlugin\bin"
DEFAULTS = dict(profile="claude-cli", region="af-south-1", cluster="graphite-cluster",
                service="graphite-prod-backend", container="graphite-backend")

QUARTERS = {1: ("01-01", "03-31"), 2: ("04-01", "06-30"),
            3: ("07-01", "09-30"), 4: ("10-01", "12-31")}

PHP_TEMPLATE = r"""
error_reporting(0);
$polno = "__POLNO__";
$termId = (int)"__TERMID__";
$start = "__START__";
$end = "__END__";
$commit = __COMMIT__;
$out = [];
if ($termId <= 0) {
  $p = DB::table('policies')->where('policyNumber',$polno)->first();
  if(!$p){ echo "##"."ZZ"."##".base64_encode(json_encode(['error'=>'policy number not found: '.$polno]))."##"."YY"."##"; return; }
  $out['policyNumber']=$p->policyNumber;
  $t = DB::table('policy_term')->where('policy_id',$p->id)->orderByDesc('id')->first();
  if(!$t){ echo "##"."ZZ"."##".base64_encode(json_encode(['error'=>'no term found for policy '.$polno]))."##"."YY"."##"; return; }
  $termId = $t->id;
}
$b = DB::table('policy_term')->where('id',$termId)->first();
if(!$b){ echo "##"."ZZ"."##".base64_encode(json_encode(['error'=>'term not found: '.$termId]))."##"."YY"."##"; return; }
$out['term_id']=(int)$termId;
$out['policy_id']=(int)$b->policy_id;
$out['before']=['start'=>substr((string)$b->term_start_date,0,10),'end'=>substr((string)$b->term_end_date,0,10),'trans_type'=>$b->trans_type,'status'=>$b->status];
$out['requested']=['start'=>$start,'end'=>$end];
if($commit){
  DB::beginTransaction();
  try {
    DB::table('policy_term')->where('id',$termId)->update(['term_start_date'=>$start,'term_end_date'=>$end,'updated_at'=>now()]);
    $a = DB::table('policy_term')->where('id',$termId)->first();
    $as=substr((string)$a->term_start_date,0,10); $ae=substr((string)$a->term_end_date,0,10);
    $out['after']=['start'=>$as,'end'=>$ae];
    if($as===$start && $ae===$end){ DB::commit(); $out['committed']=true; }
    else { DB::rollBack(); $out['committed']=false; $out['error']='verify mismatch - rolled back'; }
  } catch(\Throwable $e){ DB::rollBack(); $out['committed']=false; $out['error']=$e->getMessage(); }
} else { $out['mode']='preview'; }
echo "##"."ZZ"."##".base64_encode(json_encode($out))."##"."YY"."##";
"""


def run_php(php, args):
    env = os.environ.copy()
    env["PATH"] = PLUGIN_DIR + os.pathsep + env.get("PATH", "")
    b64 = base64.b64encode(php.encode()).decode()
    task = subprocess.check_output(
        ["aws","ecs","list-tasks","--cluster",args.cluster,"--service-name",args.service,
         "--profile",args.profile,"--region",args.region,"--query","taskArns[0]","--output","text"],
        env=env, text=True, encoding="utf-8", errors="replace").strip()
    if not task or task == "None":
        sys.exit("ERROR: no running task found for service " + args.service)
    cmd = ["aws","ecs","execute-command","--cluster",args.cluster,"--task",task,
           "--container",args.container,"--interactive",
           "--command", "sh -c 'echo %s | base64 -d | php artisan tinker'" % b64,
           "--profile",args.profile,"--region",args.region]
    raw = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    m = re.search(r"##ZZ##(.*?)##YY##", raw, re.S)
    if not m:
        sys.exit("ERROR: no result from DB. Raw tail:\n" + raw[-700:])
    return json.loads(base64.b64decode(re.sub(r"[^A-Za-z0-9+/=]", "", m.group(1))).decode())


def main():
    ap = argparse.ArgumentParser(description="Set a Graphite policy term to a calendar quarter.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--policy", help="policy number, e.g. COMG2024129498 (uses its latest term)")
    g.add_argument("--term-id", type=int, help="target a specific policy_term id")
    ap.add_argument("--quarter", type=int, required=True, choices=[1, 2, 3, 4])
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--commit", action="store_true", help="apply the change (default = preview only)")
    for k, v in DEFAULTS.items():
        ap.add_argument("--" + k, default=v)
    args = ap.parse_args()

    s, e = QUARTERS[args.quarter]
    start, end = "%d-%s" % (args.year, s), "%d-%s" % (args.year, e)
    php = (PHP_TEMPLATE
           .replace("__POLNO__", (args.policy or "").replace('"', ''))
           .replace("__TERMID__", str(args.term_id or 0))
           .replace("__START__", start).replace("__END__", end)
           .replace("__COMMIT__", "true" if args.commit else "false"))
    res = run_php(php, args)
    if res.get("error") and "before" not in res:
        sys.exit("ERROR: " + res["error"])

    print("  policy_id : %s   term_id : %s" % (res.get("policy_id"), res.get("term_id")))
    b = res["before"]
    print("  current   : %s  ->  %s   (%s, %s)" % (b["start"], b["end"], b.get("trans_type"), b.get("status")))
    print("  requested : %s  ->  %s   (Q%d %d)" % (start, end, args.quarter, args.year))
    if args.commit:
        if res.get("committed"):
            print("  RESULT    : COMMITTED OK  ->  %s  ->  %s" % (res["after"]["start"], res["after"]["end"]))
        else:
            print("  RESULT    : NOT changed - %s" % res.get("error"))
    else:
        print("  RESULT    : PREVIEW only - no change made. Re-run with --commit to apply.")


if __name__ == "__main__":
    main()
