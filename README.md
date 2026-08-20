# openIMIS Backend Medical Controller reference module
This repository holds the files of the openIMIS Backend MEdical Controller reference module.
It is dedicated to be deployed as a module of [openimis-be_py](https://github.com/openimis/openimis-be_py).

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
Here's a simple README summarizing the mutations:

```markdown README.md
# Medical Controller - GraphQL Mutations

This module defines GraphQL mutations for managing **Medical Control Missions** in openIMIS.

## Mutations

### CreateMissionMutation
Creates a new medical control mission with associated health facilities.

#### Input Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `regionId` | Int | Yes | ID of the region |
| `districtId` | Int | Yes | ID of the district |
| `healthFacilityIds` | [Int] | Yes | List of health facility IDs (at least one) |
| `startDate` | Date | Yes | Mission start date |
| `endDate` | Date | Yes | Mission end date (must be > start) |
| `status` | Int | No | Auto-set to `IN_PROGRESS` |

#### Business Rules
- Requires authentication (non-anonymous user).
- Requires `medical_controller` permissions.
- Mission code auto-generated: `{region.code}{sequence:05d}`.
- Mission status forced to `IN_PROGRESS`.
- Health facilities are bulk-created under the mission.

### UpdateMissionMutation
Same validation and permission rules apply.

## Permissions
Users must have the `gql_mutation_medical_controller_perms` permission (defined in `MedicalControllerConfig`).

## Dependencies
- `graphene`
- `openIMIS` core schema (`OpenIMISMutation`)
- `location.models.Location`
- `medical_controller.models`
```