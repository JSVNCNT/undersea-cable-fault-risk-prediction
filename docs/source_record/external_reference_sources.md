# External reference-source record

These references support the separate files in `data/external/`. They are
context and documented-event evidence only; none is joined to the synthetic
`CAB####` cable-year panel.

| Organization | Reference | Used for | URL | Accessed |
|---|---|---|---|---|
| International Telecommunication Union (ITU) | *Strengthening the world's digital backbone* | Approximately 99% of international data traffic carried by submarine cables | <https://www.itu.int/hub/2025/02/strengthening-the-worlds-digital-backbone/> | 2026-09-16 |
| ITU | *Global Connectivity Report 2025*, chapter 3 | 86% human-activity fault share; 22% annual bandwidth growth since 2021 | <https://www.itu.int/itu-d/reports/statistics/2025/11/17/gcr-2025-chapter-3/> | 2026-09-16 |
| ITU | *Submarine cable resilience* backgrounder | Over 170 repairs reported worldwide in 2025; approximately 200,000 km installed in 2024 | <https://www.itu.int/en/mediacentre/backgrounders/Pages/submarine-cable-resilience.aspx> | 2026-09-16 |
| ITU | ITU-T G Supplement 41 (05/2005) | Typical 25-year submarine-system design life | <https://www.itu.int/rec/dologin_pub.asp?id=T-REC-G.Sup41-200505-S%21%21PDF-E&lang=e&type=items> | 2026-09-16 |
| International Cable Protection Committee (ICPC) | *Damage to Submarine Cables Caused by Anchors* (Loss Prevention Bulletin, 2009) | Historical fishing/anchor distributions through 2006 and UK 2007–2008 | <https://www.iscpc.org/documents/?id=139> | 2026-09-16 |
| TeleGeography | *Written testimony on submarine cable security* | Approximate annual faults and selected documented anchor-drag incidents | <https://resources.telegeography.com/hubfs/Tim%20Stronge%20Written%20Congressional%20Testimony%20%7C%20TeleGeography.pdf> | 2026-09-16 |

## Interpretation safeguards

- Published percentages have their original scope and period retained in the
  CSV. Historical ICPC percentages must not be presented as current global
  rates.
- The TeleGeography incident list is a selected compilation, not a complete
  incident census. Empty cable-count cells mean the source did not provide a
  numeric telecom-cable count, not zero incidents.
- ITU and ICPC figures describe the real-world sector; the Kaggle panel remains
  explicitly synthetic. External values therefore cannot validate or calibrate
  the model without a real cable identifier/geometry crosswalk.

## Research-rationale references (added 2026-10-03)

These are narrative background references, not additional model datasets.

| Organization | Reference | Used for | URL | Verified |
|---|---|---|---|---|
| ITU | *Restoring connectivity in Tonga through collaborative disaster response* (10 February 2022) | Documented cable disruption and temporary emergency connectivity; illustrates why alternatives and recovery matter, without claiming the model predicted the event | <https://www.itu.int/hub/2022/02/restoring-connectivity-tonga-internet/> | 2026-10-03 |
| World Bank | *Unlocking the Philippines' Digital Transformation by Increasing Internet Connectivity* (2 July 2025) | Philippine relevance of connectivity to education, healthcare, financial inclusion and disaster resilience; not a Philippine cable-fault assessment | <https://www.worldbank.org/en/results/2025/07/02/unlocking-the-philippines-digital-transformation-by-increasing-internet-connectivity> | 2026-10-03 |

The existing ITU 2025 connectivity chapter and April 2026 resilience
backgrounder were also rechecked on 2026-10-03. Their discussion of repair
delays strengthens the research motivation. No cited fact has been copied
onto a cable-year record, and no new failure-frequency series was inferred.
