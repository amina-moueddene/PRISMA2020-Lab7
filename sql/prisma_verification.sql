-- ============================================================================
-- LAB 7 — Construction et vérification arithmétique du diagramme PRISMA 2020
-- Revue systématique : Machine learning and remote sensing for disease and stress detection in olive
-- Compatible SQLite 3 / PostgreSQL / MySQL 8+
-- ============================================================================

DROP TABLE IF EXISTS identification;
DROP TABLE IF EXISTS screening_ledger;
DROP TABLE IF EXISTS rapports_etudes;
DROP TABLE IF EXISTS exclusions_texte_integral;
DROP VIEW IF EXISTS v_verification_prisma;
DROP VIEW IF EXISTS v_controles_coherence;

-- ----------------------------------------------------------------------------
-- Étape 2 : Table Identification (nombres bruts par base de données)
-- ----------------------------------------------------------------------------
CREATE TABLE identification (
    base VARCHAR(100) PRIMARY KEY,
    nombre INTEGER NOT NULL CHECK (nombre >= 0),
    date_recherche VARCHAR(20),
    champ VARCHAR(50)
);

INSERT INTO identification (base, nombre, date_recherche, champ) VALUES
    ('Scopus', 118, '15/11/2026', 'TITLE-ABS-KEY'),
    ('Web of Science Core Collection', 97, '15/11/2026', 'TS');

-- ----------------------------------------------------------------------------
-- Étape 3 : Table de liaison Reports -> Studies
-- ----------------------------------------------------------------------------
CREATE TABLE rapports_etudes (
    record_rapport INTEGER PRIMARY KEY,
    etude INTEGER NOT NULL,
    commentaire TEXT
);

INSERT INTO rapports_etudes (record_rapport, etude, commentaire) VALUES
    (35, 109, 'Makhloufi 2022 (IGARSS) et Kallel 2022 (ACM) décrivent la même étude');

-- ----------------------------------------------------------------------------
-- Étapes 4 à 11 : Registre de tri (143 notices uniques après déduplication)
-- ----------------------------------------------------------------------------
CREATE TABLE screening_ledger (
    record INTEGER PRIMARY KEY,
    first_author VARCHAR(100),
    year INTEGER,
    doi VARCHAR(255),
    decision_stage VARCHAR(60) NOT NULL,
    final_decision VARCHAR(60) NOT NULL,
    code_motif VARCHAR(10),
    reason TEXT
);

-- ----------------------------------------------------------------------------
-- Étape 10 : Table des exclusions après évaluation du texte intégral
-- ----------------------------------------------------------------------------
CREATE TABLE exclusions_texte_integral (
    record_slr INTEGER PRIMARY KEY,
    doi VARCHAR(255) NOT NULL,
    premier_auteur VARCHAR(100),
    annee INTEGER,
    code VARCHAR(10) NOT NULL,
    motif VARCHAR(120) NOT NULL,
    commentaire TEXT NOT NULL
);

-- ----------------------------------------------------------------------------
-- Vue de calcul complet du flux PRISMA 2020 (Étapes 2 à 11)
-- ----------------------------------------------------------------------------
CREATE VIEW v_verification_prisma AS
WITH stats AS (
    SELECT
        (SELECT SUM(nombre) FROM identification) AS identifies,
        (SELECT COUNT(*) FROM screening_ledger) AS examines,
        (SELECT COUNT(*) FROM screening_ledger
         WHERE decision_stage NOT IN ('Full text', 'Title/abstract (full text not retrieved)')) AS exclus_titre_resume,
        (SELECT COUNT(*) FROM screening_ledger
         WHERE decision_stage IN ('Full text', 'Title/abstract (full text not retrieved)')) AS recherches,
        (SELECT COUNT(*) FROM screening_ledger
         WHERE decision_stage = 'Title/abstract (full text not retrieved)') AS non_recuperes,
        (SELECT COUNT(*) FROM screening_ledger
         WHERE decision_stage = 'Full text') AS evalues,
        (SELECT COUNT(*) FROM screening_ledger
         WHERE decision_stage = 'Full text' AND final_decision LIKE 'Excluded%') AS exclus_texte_integral,
        (SELECT COUNT(*) FROM screening_ledger
         WHERE decision_stage = 'Full text' AND final_decision = 'Included') AS rapports_inclus,
        (SELECT COUNT(DISTINCT COALESCE(re.etude, sl.record))
         FROM screening_ledger sl
         LEFT JOIN rapports_etudes re ON sl.record = re.record_rapport
         WHERE sl.decision_stage = 'Full text' AND sl.final_decision = 'Included') AS etudes_incluses
)
SELECT
    identifies,
    (identifies - examines) AS doublons_supprimes,
    examines,
    exclus_titre_resume,
    recherches,
    non_recuperes,
    evalues,
    exclus_texte_integral,
    rapports_inclus,
    etudes_incluses
FROM stats;

-- ----------------------------------------------------------------------------
-- Étape 11 : Contrôles automatiques de cohérence arithmétique PRISMA
-- ----------------------------------------------------------------------------
CREATE VIEW v_controles_coherence AS
SELECT
    CASE WHEN identifies = doublons_supprimes + examines THEN 'OK' ELSE 'ERREUR' END AS ctrl_deduplication,
    CASE WHEN recherches = examines - exclus_titre_resume THEN 'OK' ELSE 'ERREUR' END AS ctrl_screening,
    CASE WHEN evalues = recherches - non_recuperes THEN 'OK' ELSE 'ERREUR' END AS ctrl_textes_evalues,
    CASE WHEN rapports_inclus = evalues - exclus_texte_integral THEN 'OK' ELSE 'ERREUR' END AS ctrl_rapports_inclus,
    CASE WHEN etudes_incluses <= rapports_inclus THEN 'OK' ELSE 'ERREUR' END AS ctrl_etudes_vs_rapports
FROM v_verification_prisma;

-- ----------------------------------------------------------------------------
-- Étape 13 : Vérification SQL du Défi 1 (tableau avec incohérences corrigé)
-- ----------------------------------------------------------------------------
SELECT
    950 AS identifies,
    200 AS doublons,
    (950 - 200) AS examines_corrige,             -- 750 (au lieu de 800)
    500 AS exclus_titre_resume,
    (950 - 200 - 500) AS recherches_corrige,     -- 250 (au lieu de 300)
    10 AS non_recuperes,
    (250 - 10) AS evalues_valide,                -- 240 (OK)
    (95 + 50 + 30) AS exclusions_corrige,        -- 175 (au lieu de 180)
    (240 - (95 + 50 + 30)) AS incluses_corrige;  -- 65  (au lieu de 70)
