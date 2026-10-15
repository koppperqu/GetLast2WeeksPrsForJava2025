# GetLast2WeeksPrsForJava2025

The producer side of [Better_Tfrrs_Website](https://github.com/koppperqu/Better_Tfrrs_Website), a DIII track & field stats site. This is the Python half that produces data for the Spring Boot application to render.

## Why it exists

The Java app collects season bests from TFRRS team and athlete pages. Personal records set *at a meet* live somewhere else — in the meet result pages, where TFRRS marks them with `<tr class="highlight">`. This script reads those pages and writes one JSON file per team, which the website displays as a "recent PRs" section on the team page.

This logic wasn't written for the Java version. It came from an earlier Django version of the same site and was carried over during the port — the output shape is what the Java side expects, not the other way around.

## How it works

```
conference page  →  team links and names
team page        →  roster links (women's derived from men's by swapping _m_ / _f_ in the URL)
athlete page     →  that athlete's two most recent meets
                   ↳ keep a meet only if it's also one of the *team's* two most recent
                   ↳ collect the highlight rows
  →  group PRs by date, then by meet, write {team}_recentrPRs.json
```

Output is one file per team, written next to the script. The committed files are real sample output.

```json
[
    {
        "meetname": "American Rivers Conference Championships",
        "meetdate": "May 08, 2025",
        "numberofprs": 11,
        "uniqueprs": 8,
        "prsatmeet": [
            { "athletename": "Scott Drouillard", "eventname": "HT", "pr": "31.65m" }
        ]
    }
]
```

`numberofprs` counts performances, `uniqueprs` counts athletes. They differ because one athlete can set PRs in several events at the same meet.

## How it connects to the Java app

`TeamController` reads the directory set by the `last2weeksprsjson` property and resolves one file per team by convention — team name, spaces to hyphens, lowercased, plus `_recentrPRs.json` — then deserializes it into `MeetDTO`. There is no manifest and no shared config; the filename *is* the contract. A missing or malformed file is caught and returns an empty list, so the page renders with the section blank rather than failing.

Note that this repo and the Java repo are separate. This script writes to its own directory; the files need to be copied into `Last2WeeksPrsJson/` in the Java repo for the site to pick them up.

## Usage

```
pip install beautifulsoup4
python getAllTeamsLast2WeeksPRs.py
```

Scrapes the WIAC (league 1420) then American Rivers (league 1400). It's one request per athlete per gender per team, so a full run is thousands of requests and takes a while; per-team progress prints to the console. Failed requests retry five times with exponential backoff (10s, 20s, 40s, 80s) and then exit.

Both conference URLs are constants at the bottom of the script and the scrape function takes a URL argument, so adding a conference is a one-line change.

## Notes

- The original version decided whether a meet was recent with `lastXMeets[meetIndex] in eachMeet` — substring containment against a single meet URL. It now checks `eachMeet in lastXMeets`, matching the athlete's meet against the team's full list of recent meet URLs. The old form would match on any shared substring.
- Deriving the women's roster from the men's team URL by swapping `_m_` for `_f_` is how TFRRS structures its links, but it is still a string heuristic.
- Offseason, a team page can list fewer than two recent meets. The script indexes the first two without a length check and will raise `IndexError` there.
- This script and the Java scraper derive team names from different sources — TFRRS display text here, the URL slug there. That's worth checking if a team's section renders empty, since Wisconsin schools and names with parentheses are where the two are most likely to disagree.