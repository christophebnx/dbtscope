# large-data-vault: a generated Data Vault estate of 1,419 tables (M8.1)

Input: none committed. The input is the generator `tests/large_project.py` (`large_manifest()`,
deterministic, `random.Random(1374)`), because a committed manifest would be several MB and a second
source of truth next to its generator (D-033's reasoning). Synthetic: made-up entities, no real data.
`expected.json` holds the counts the generator must give (`tests/unit/test_large_project.py`).

Shape (an Openlane-style Data Vault, brief `docs/briefs/2026-11-12-m8-synthesis.md` § 2):

- 7 source systems (`crm erp dms lms pay tms web`), 36 sources each and one raw staging model per
  source (`models/raw_<system>/`, schema `raw_<system>`): 252 + 252;
- 5 business domains (`vehicle auction account claim activity`) in `models/int_dwh/<domain>/` (schema =
  the domain): 175 hubs, 191 links (about one in five has a hub of another domain), 422 satellites
  (1 to 4 per hub, plus effectivity satellites on some links), 20 PITs, 25 stage models
  `stg_<domain>__<entity>` and 20 views `vw_<entity>`;
- 31 dimensions and 31 facts in `models/dp_dwh/<domain>/`;
- 978 relations from `relationships` tests, 1,643 lineage links, source to staging to vault stage models
  to the vault to the data products.

Special satellites (`SPECIAL`, for the satellite-to-hub rules of M8.2): `no_relation_by_name` (no
relation, its name starts with an existing hub's stem), `no_parent` (no relation, no stem matches),
`two_parents` (relations to two hubs, one stem a prefix of its name), `other_domain` (in `vehicle`, its
relation points to an `auction` hub) and `effectivity_on_link` (an effectivity satellite whose parent is
a link).

Fold counts (M8.2, `expected.json` `fold`, D-062): 442 descriptive tables (422 satellites including the
effectivity satellites, 20 PITs), 440 folded, 2 without a parent (`orphan_ledger_sat`: no relation and no
stem; `auction_vehicle_sat`: its parent is in another domain), 428 entities (175 hubs, 191 links, 31
dimensions, 31 facts), 388 of the 828 Raw vault tables drawn as stars. Expected parent of each special
satellite: `no_relation_by_name` into `car_hub` (by name), `two_parents` into `van_hub` (the relation
to `bus_hub` loses to the name), `effectivity_on_link` into its link, `no_parent` and `other_domain` none.

Used with `LARGE_CONFIG` (`preset: data_vault` and the five domain labels); the universe then has no
"Other" table and four layers (Sources, Staging, Raw vault, Data products).
