"""The domain error taxonomy.

Every failure the engine reports is one of these, and every one carries a
stable code. The codes are the contract: the interface switches on them, the
support bundle groups by them, and renaming one is a breaking change.

Nothing here imports anything outside the standard library, which is the whole
point of the domain layer.
"""

from __future__ import annotations


class RomSyncError(Exception):
    """Base of the taxonomy. Never raised directly."""

    code = "romsync.error"

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field

    def as_envelope(self) -> dict[str, str | None]:
        """The single error shape the HTTP layer serialises."""
        return {"code": self.code, "message": self.message, "field": self.field}


# --- paths and containment ---------------------------------------------------


class PathEscape(RomSyncError):
    """A path resolved outside the root it was constructed against."""

    code = "path.escape"


class NotAName(RomSyncError):
    """A single name was required and something path-shaped was given."""

    code = "path.not_a_name"


# --- configuration -----------------------------------------------------------


class UnknownConfigKey(RomSyncError):
    """A key that the registry does not declare."""

    code = "config.unknown_key"


class ConfigOutOfRange(RomSyncError):
    """A value outside the range or allowed set the registry declares."""

    code = "config.out_of_range"


class ConfigWrongType(RomSyncError):
    """A value whose type the registry does not accept."""

    code = "config.wrong_type"


class ConfigMissing(RomSyncError):
    """A value with no default that nothing has set."""

    code = "config.missing"


# --- store and library -------------------------------------------------------


class StoreUnreadable(RomSyncError):
    """The store root, or something required inside it, could not be read."""

    code = "store.unreadable"


class SystemFileUnreadable(RomSyncError):
    """A system's own descriptor could not be read, so its games are unknown."""

    code = "store.system_file_unreadable"


class GameNotFound(RomSyncError):
    """No game has that id."""

    code = "game.not_found"


class CoverNotFound(RomSyncError):
    """No game's cover is stored under that name."""

    code = "cover.not_found"


class NothingIndexed(RomSyncError):
    """A scan indexed no systems, so a prune would delete everything."""

    code = "store.nothing_indexed"


class WouldOverwrite(RomSyncError):
    """Placing a file in the store would replace one already there."""

    code = "store.would_overwrite"


# --- destinations ------------------------------------------------------------


class DestinationUnavailable(RomSyncError):
    """The destination is not reachable now."""

    code = "dest.unavailable"


class DestinationRootMissing(RomSyncError):
    """The destination's root does not exist and was not created."""

    code = "dest.root_missing"


class ProfileNotFound(RomSyncError):
    """No device profile has that id."""

    code = "profile.not_found"


class BadDeviceRef(RomSyncError):
    """Text that is not the canonical reference of any device."""

    code = "dest.bad_reference"


class UnknownDevice(RomSyncError):
    """A well-formed reference to a device that is not attached."""

    code = "dest.unknown_device"


class DestinationItemMissing(RomSyncError):
    """An item asked for by name is not on the destination."""

    code = "dest.item_missing"


class DestinationToolMissing(RomSyncError):
    """The program a transport is driven through is not installed."""

    code = "dest.tool_missing"


class CapabilityUnsupported(RomSyncError):
    """A port was asked of an adapter that does not declare it."""

    code = "dest.capability_unsupported"


class TransferFailed(RomSyncError):
    """One operation failed. The run reports it; it never passes silently."""

    code = "dest.transfer_failed"


class VerificationFailed(RomSyncError):
    """A transferred item did not match its source."""

    code = "dest.verification_failed"


class MarkerUntrusted(RomSyncError):
    """A device marker carried a path that failed validation on ingress."""

    code = "dest.marker_untrusted"


# --- the desktop shell --------------------------------------------------------


class ShellUnavailable(RomSyncError):
    """The shell endpoints answer only while the server listens on loopback."""

    code = "shell.unavailable"


class LinkRefused(RomSyncError):
    """A link that is not https to a site on the allow-list."""

    code = "shell.link_refused"


# --- guards ------------------------------------------------------------------


class GuardRefused(RomSyncError):
    """A destructive operation named something the guards protect."""

    code = "guard.refused"


class ConfirmRemovals(RomSyncError):
    """A sync removing this many games needs the count confirmed first."""

    code = "sync.confirm_removals"


class DryRunFirst(RomSyncError):
    """A destructive maintenance run did not name the count its dry run found."""

    code = "maintenance.dry_run_first"


class DoesNotFit(RomSyncError):
    """The plan's peak usage exceeds the destination's capacity."""

    code = "plan.does_not_fit"


# --- metadata ----------------------------------------------------------------


class MetadataCredentialsMissing(RomSyncError):
    """The metadata client was composed without credentials."""

    code = "metadata.credentials_missing"


class MetadataRejected(RomSyncError):
    """The metadata service rejected the credentials."""

    code = "metadata.rejected"


class MetadataThrottled(RomSyncError):
    """The metadata service asked us to slow down."""

    code = "metadata.throttled"


class MetadataUnreachable(RomSyncError):
    """The metadata service could not be reached."""

    code = "metadata.unreachable"


class MetadataFailed(RomSyncError):
    """The metadata service refused a query for a reason other than credentials."""

    code = "metadata.failed"


class MetadataNotFound(RomSyncError):
    """The metadata service has no game by that reference."""

    code = "metadata.not_found"


# --- persistence -------------------------------------------------------------


class SchemaTooNew(RomSyncError):
    """The database was written by a later version of the application."""

    code = "db.schema_too_new"


class MigrationFailed(RomSyncError):
    """A migration step failed. The pre-migration backup is retained."""

    code = "db.migration_failed"


# --- jobs --------------------------------------------------------------------


class JobConflict(RomSyncError):
    """A job of a conflicting kind is already running against this target."""

    code = "job.conflict"


class JobNotFound(RomSyncError):
    """No job has that id."""

    code = "job.not_found"


class JobCancelled(RomSyncError):
    """The job stopped because its cancel token was set."""

    code = "job.cancelled"


class JobFailed(RomSyncError):
    """A job's worker raised something outside the taxonomy."""

    code = "job.failed"


class JobInterrupted(RomSyncError):
    """The job was running when the process stopped. Found at startup."""

    code = "job.interrupted"
