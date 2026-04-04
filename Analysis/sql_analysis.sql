-- HOSPITAL ANALYTICS SOLUTIONS
USE hosp_analysis;

-- OBJECTIVE 1: ENCOUNTERS OVERVIEW

-- 1a. How many total encounters occurred each year?

SELECT
    YEAR(Start) AS encounter_year,
    COUNT(*) AS total_encounters
FROM encounters
GROUP BY YEAR(Start)
ORDER BY encounter_year;


-- 1b. For each year, what percentage of all encounters belonged to each encounter class?

SELECT
    YEAR(Start) AS encounter_year,
    EncounterClass,
    COUNT(*) AS class_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY YEAR(Start)),2
    ) AS pct_of_year
FROM encounters
GROUP BY YEAR(Start), EncounterClass
ORDER BY encounter_year, pct_of_year DESC;


-- 1c. What percentage of encounters were over 24 hours vs under 24 hours?

SELECT
    CASE WHEN TIMESTAMPDIFF(HOUR, Start, Stop) >= 24 THEN 'Over 24 Hours'
        ELSE 'Under 24 Hours'
    END AS duration_category,
    COUNT(*) AS total_encounters,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM encounters), 2) AS pct_of_total
FROM encounters
GROUP BY duration_category;



-- OBJECTIVE 2: COST & COVERAGE INSIGHTS

-- 2a. How many encounters had zero payer coverage, and what percentage of total encounters does this represent?

SELECT
    COUNT(*) AS zero_coverage_encounters,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM encounters),2
    ) AS pct_of_total
FROM encounters
WHERE Payer_Coverage = 0;


-- 2b. Top 10 most frequent procedures and average base cost for each.

SELECT
    Description AS procedure_name,
    COUNT(*) AS times_performed,
    ROUND(AVG(Base_Cost), 2) AS avg_base_cost
FROM procedures
GROUP BY Description
ORDER BY times_performed DESC
LIMIT 10;


-- 2c. Top 10 procedures with the highest average base cost and the number of times they were performed.

SELECT
    Description AS procedure_name,
    ROUND(AVG(Base_Cost), 2) AS avg_base_cost,
    COUNT(*) AS times_performed
FROM procedures
GROUP BY Description
ORDER BY avg_base_cost DESC
LIMIT 10;


-- 2d. Average total claim cost for encounters, broken down by payer.

SELECT
    py.NAME AS payer_name,
    COUNT(e.Id) AS total_encounters,
    ROUND(AVG(e.Total_Claim_Cost), 2) AS avg_total_claim_cost
FROM encounters e
JOIN payers py ON e.Payer = py.Id
GROUP BY py.NAME
ORDER BY avg_total_claim_cost DESC;


-- OBJECTIVE 3: PATIENT BEHAVIOR ANALYSIS

-- 3a. How many unique patients were admitted each quarter over time?

SELECT
    YEAR(Start) AS encounter_year,
    QUARTER(Start) AS encounter_quarter,
    COUNT(DISTINCT Patient) AS unique_patients
FROM encounters
GROUP BY YEAR(Start), QUARTER(Start)
ORDER BY encounter_year, encounter_quarter;


-- 3b. How many patients were readmitted within 30 days of a previous encounter?

-- 3b (fixed)
WITH encounter_pairs AS (
    SELECT
        e1.Patient,
        e1.Id AS first_encounter,
        e2.Id AS readmission_encounter,
        e1.Start AS first_start,
        e2.Start AS readmit_start,
        DATEDIFF(e2.Start, e1.Stop) AS days_between
    FROM encounters e1
    JOIN encounters e2
        ON e1.Patient = e2.Patient
        AND e2.Start > e1.Stop
        AND DATEDIFF(e2.Start, e1.Stop) <= 30
        AND e1.Id != e2.Id
)
SELECT
    COUNT(DISTINCT Patient) AS patients_readmitted_within_30_days
FROM encounter_pairs;


-- 3c. Which patients had the most readmissions?

WITH encounter_pairs AS (
    SELECT
        e1.Patient,
        e2.Id AS readmission_encounter
    FROM encounters e1
    JOIN encounters e2
        ON e1.Patient = e2.Patient
        AND e2.Start > e1.Stop
        AND DATEDIFF(e2.Start, e1.Stop) <= 30
        AND e1.Id != e2.Id
)
SELECT
    ep.Patient AS patient_id,
    CONCAT(p.FIRST, ' ', p.LAST) AS patient_name,
    COUNT(ep.readmission_encounter) AS readmission_count
FROM encounter_pairs ep
JOIN patients p ON ep.Patient = p.Id
GROUP BY ep.Patient, patient_name
ORDER BY readmission_count DESC
LIMIT 10;
