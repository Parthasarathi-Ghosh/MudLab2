"""Deep uuid remapping for imported objects (phases, components).

Shared by the .phs and .cmp importers. uuids are 32 lowercase-hex
(uuid1/uuid4 .hex), so a plain string replace over the serialised JSON catches
EVERY reference - the object's own uuid, based_on_uuid, linked_with, atom
relations (stored as list elements) and UCP derivation sources - without having
to know the schema. Audited against the real default-phase library: every
32-hex string there is a quoted uuid (colours are 6-hex, ref_info are numbers,
no 33+ hex runs), so there are no false positives.
"""

from __future__ import annotations

import re
import uuid as _uuid

UUID_RE = re.compile(r"[0-9a-f]{32}")


def project_uuids(project) -> set:
    """Every uuid live in the project - phases, components and atoms."""
    uuids = set()
    for phase in project.phases:
        uuids.add(phase.uuid)
        for comp in getattr(phase, "components", []):
            uuids.add(comp.uuid)
            for atom in comp._layer_atoms + comp._interlayer_atoms:
                uuids.add(atom.uuid)
    return uuids


def remap_uuids(texts, blocked) -> tuple[list, dict]:
    """Return (texts, remap): every uuid in `texts` that is also in `blocked`
    gets a fresh uuid, replaced consistently across all texts. Fresh uuids are
    guarded against the project, the whole import and each other, so a
    replacement can never alias a kept uuid.

    Pass the project's uuids to remap only COLLISIONS (phase import keeps
    non-colliding uuids); pass the import's own uuids to force EVERY uuid fresh
    (component import, whose objects replace existing ones)."""
    blocked = set(blocked)
    import_uuids = set()
    for text in texts:
        import_uuids.update(UUID_RE.findall(text))
    taken = blocked | import_uuids
    remap: dict[str, str] = {}
    for old in sorted(import_uuids & blocked):
        new = _uuid.uuid4().hex
        while new in taken:
            new = _uuid.uuid4().hex
        taken.add(new)
        remap[old] = new
    for old, new in remap.items():
        texts = [text.replace(old, new) for text in texts]
    return texts, remap
