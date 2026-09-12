"""M365 licence-activity tracking.

The Friday sync command (`sync_m365_active_users`) calls Microsoft Graph
with a service-principal token, fetches users whose last interactive
sign-in is within the last 6 months (configurable), and writes them here.

Shared/forward mailboxes and disabled accounts are excluded by the
service layer before they reach this table.
"""
from __future__ import annotations

from django.db import models


class M365ActiveUser(models.Model):
    """One row per active licensed human user (real, not a shared mailbox).

    Refreshed every Friday morning. `last_interactive_signin_at` mirrors
    Graph `signInActivity.lastSignInDateTime`.
    """
    object_id = models.CharField(max_length=64, unique=True)  # Entra OID
    email = models.EmailField(max_length=255, db_index=True)
    display_name = models.CharField(max_length=255)
    user_principal_name = models.CharField(max_length=255, db_index=True)
    job_title = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    license_count = models.PositiveIntegerField(default=0)
    last_interactive_signin_at = models.DateTimeField(null=True, blank=True)
    refreshed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("display_name",)

    def __str__(self) -> str:
        return f"{self.display_name} <{self.email}>"


class M365LicenseSyncRun(models.Model):
    """Audit row per sync execution — lets the Settings page show the
    last refresh time and whether the previous run succeeded."""
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    total_seen = models.PositiveIntegerField(default=0)
    active_count = models.PositiveIntegerField(default=0)
    inserted = models.PositiveIntegerField(default=0)
    updated = models.PositiveIntegerField(default=0)
    removed = models.PositiveIntegerField(default=0)
    success = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    cutoff_at = models.DateTimeField(null=True, blank=True)
    triggered_by = models.CharField(max_length=64, default="cron")

    class Meta:
        ordering = ("-started_at",)

    def __str__(self) -> str:
        flag = "ok" if self.success else "FAIL"
        return f"sync {self.started_at:%Y-%m-%d %H:%M} {flag} active={self.active_count}"
