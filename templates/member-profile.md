---
type: person
name: "{{NAME}}"
role: "{{ROLE}}"
email: "{{EMAIL}}"
clickup_id: {{CLICKUP_ID}}
slack_id: "{{SLACK_ID}}"
status: active
aliases:
  - {{FIRST_NAME}}
---

# {{NAME}}

## Background & Strengths

<!-- Professional background, key skills, what they excel at -->

---

## Current Responsibilities

- ...
- ...

---

## Career Goals & Aspirations

### Short-term (6-12 months)
<!-- What they want to achieve in the near future -->

### Long-term (1-3 years)
<!-- Where they see themselves going -->

---

## Areas for Development

<!-- Skills, behaviors, or competencies that need growth -->

- ...
- ...

---

## Communication Style

- **Preferred feedback style:**
- **Communication preferences:**
- **How they handle conflict:**
- **What motivates them:**

---

## Personal Profile

<!-- Personality traits, hobbies, interests, what they enjoy outside of work -->

- **Hobbies & interests:**
- **What they enjoy doing on weekends:**
- **Personality traits (self-described or observed):**
- **Fun facts:**

---

## Dreams & Life Goals

<!-- Personal aspirations beyond career — travel, family, lifestyle, personal projects, etc. -->

---

## Company Expectations

<!-- What they expect from the company, from their manager, from the team -->

- **From the company:**
- **From the manager:**
- **From the team:**
- **Work environment preferences:**

---

## Important Dates

| Date       | Event                |
|------------|----------------------|
|            | Birthday             |
|            | Work anniversary     |
|            |                      |

---

## Recent Meetings

```dataview
TABLE date AS "Date", subtype AS "Type"
FROM #meeting
WHERE contains(file.outlinks, this.file.link)
SORT date DESC
LIMIT 5
```

## Manager Notes

<!-- Private observations, patterns noticed, things to watch for -->