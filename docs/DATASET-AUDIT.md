# Supplied Luma dataset audit

Inspected the supplied CSV locally and imported it through the application pipeline into a private temporary database. This report contains aggregate observations and column names only. No real attendee identities or responses are included in the source package.

| Observation | Result |
|---|---:|
| Rows | 96 |
| Columns | 52 |
| Approved | 90 |
| Declined | 6 |
| Duplicate guest IDs | 0 |
| Duplicate normalized emails | 0 |
| Offline availability: yes (all registrations) | 63 |
| Offline availability: unknown (all registrations) | 33 |
| Approved + confirmed offline availability | 61 |
| Approved + unknown offline availability | 29 |
| Approved records missing default required skills/goals/schedule | 0 |

These counts are observations, never application constants. There are no real participant accounts in the delivered package and no live verified matching pool. Approval alone does not prove email ownership or enter a registration window. If all 90 approved participants independently verified and joined, the arithmetic maximum would be 30 teams; with mandatory offline confirmation and no further resolutions, the 61 currently confirmed approved records would allow 20 teams plus one waitlisted person. Neither scenario was activated.

## Every source column

The importer accepts these exact names, preserves all columns privately, and maps the fourteen questionnaire columns explicitly. Gender and identifiers never enter compatibility scoring. Filled/distinct counts include the blank category in the distinct count.

| # | Exact source column | Filled | Distinct values | Use |
|---:|---|---:|---:|---|
| 1 | `guest_id` | 96 | 96 | Registration identity |
| 2 | `name` | 96 | 95 | Display identity only |
| 3 | `first_name` | 95 | 84 | Private source metadata; excluded from matching |
| 4 | `last_name` | 90 | 74 | Private source metadata; excluded from matching |
| 5 | `email` | 96 | 96 | Registration identity |
| 6 | `phone_number` | 96 | 94 | Private source metadata; excluded from matching |
| 7 | `created_at` | 96 | 96 | Private source metadata; excluded from matching |
| 8 | `approval_status` | 96 | 2 | Eligibility |
| 9 | `checked_in_at` | 0 | 1 | Private source metadata; excluded from matching |
| 10 | `utm_source` | 0 | 1 | Private source metadata; excluded from matching |
| 11 | `utm_medium` | 0 | 1 | Private source metadata; excluded from matching |
| 12 | `utm_campaign` | 0 | 1 | Private source metadata; excluded from matching |
| 13 | `utm_term` | 0 | 1 | Private source metadata; excluded from matching |
| 14 | `utm_content` | 0 | 1 | Private source metadata; excluded from matching |
| 15 | `google_click_id` | 0 | 1 | Private source metadata; excluded from matching |
| 16 | `meta_click_id` | 0 | 1 | Private source metadata; excluded from matching |
| 17 | `x_click_id` | 0 | 1 | Private source metadata; excluded from matching |
| 18 | `linkedin_click_id` | 0 | 1 | Private source metadata; excluded from matching |
| 19 | `tiktok_click_id` | 0 | 1 | Private source metadata; excluded from matching |
| 20 | `reddit_click_id` | 0 | 1 | Private source metadata; excluded from matching |
| 21 | `yandex_click_id` | 0 | 1 | Private source metadata; excluded from matching |
| 22 | `referrer` | 42 | 9 | Private source metadata; excluded from matching |
| 23 | `referred_by` | 8 | 7 | Private source metadata; excluded from matching |
| 24 | `qr_code_url` | 96 | 96 | Private source metadata; excluded from matching |
| 25 | `amount` | 90 | 2 | Private source metadata; excluded from matching |
| 26 | `amount_tax` | 90 | 2 | Private source metadata; excluded from matching |
| 27 | `amount_discount` | 90 | 2 | Private source metadata; excluded from matching |
| 28 | `currency` | 90 | 2 | Private source metadata; excluded from matching |
| 29 | `coupon_code` | 0 | 1 | Private source metadata; excluded from matching |
| 30 | `eth_address` | 0 | 1 | Private source metadata; excluded from matching |
| 31 | `solana_address` | 0 | 1 | Private source metadata; excluded from matching |
| 32 | `survey_response_rating` | 0 | 1 | Private source metadata; excluded from matching |
| 33 | `survey_response_feedback` | 0 | 1 | Private source metadata; excluded from matching |
| 34 | `ticket_type_id` | 90 | 2 | Private source metadata; excluded from matching |
| 35 | `ticket_name` | 90 | 2 | Private source metadata; excluded from matching |
| 36 | `SAP ID (if from NMIMS)` | 34 | 31 | Private source metadata; excluded from matching |
| 37 | `College/University/School Name` | 79 | 60 | Questionnaire / profile context |
| 38 | `Year of study (eg: 1, 2, 3, 4)` | 96 | 18 | Questionnaire / profile context |
| 39 | `Gender` | 96 | 2 | Private source metadata; excluded from matching |
| 40 | `Skills` | 96 | 43 | Questionnaire / profile context |
| 41 | `What's your main goal for this hackathon?` | 96 | 51 | Questionnaire / profile context |
| 42 | `Do you want to work in your strongest area or stretch into a weaker one?` | 96 | 3 | Questionnaire / profile context |
| 43 | `Have you done a hackathon before?` | 96 | 3 | Questionnaire / profile context |
| 44 | `When are you most productive during the event?` | 96 | 15 | Questionnaire / profile context |
| 45 | `How do you handle disagreements?` | 96 | 3 | Questionnaire / profile context |
| 46 | `Do you naturally take the lead in groups?` | 96 | 3 | Questionnaire / profile context |
| 47 | `Hobbies` | 96 | 92 | Questionnaire / profile context |
| 48 | `Describe yourself in one word` | 96 | 79 | Questionnaire / profile context |
| 49 | `What's your Instagram feed like` | 96 | 62 | Questionnaire / profile context |
| 50 | `Background soundtrack while coding` | 96 | 44 | Questionnaire / profile context |
| 51 | `Refereed by?` | 31 | 28 | Private source metadata; excluded from matching |
| 52 | `If selected you will be available to come for offline round at mpstme mumbai campus` | 63 | 2 | Questionnaire / profile context |

## Normalization observations

- Skills contain comma-separated combinations, not one category per participant. The actual selections are Front End, Backend, Full stack, UI/UX and Presenting / public speaking.
- Main goals and productivity periods also contain multiple selections and inconsistent ordering. They are normalized as sets.
- Actual experience choices are Never, 1–2 and 3+. Leadership choices are Rarely, Sometimes and Usually.
- Actual conflict-resolution choices are Debate it out, Vote and Defer to whoever owns that part. They remain soft signals.
- Years include numeric values, ordinals, text shorthand, graduated responses and an out-of-range value. Unresolved values stay unknown; academic year is not scored.
- College is blank in 17 records. Offline availability is blank in 33. Those blanks do not become negative answers.
- Original text is preserved. Tokenization of hobbies and feed descriptions makes no claims about personality or ability.
- The real source CSV and the temporary audit database are excluded from the deliverable.
