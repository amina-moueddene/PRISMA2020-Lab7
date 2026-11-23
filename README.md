# LAB 7 : Construire le diagramme de flux PRISMA 2020
**Application à ma SLR : ML et télédétection pour la détection des maladies et du stress de l'olivier**

> Les nombres viennent de ma SLR (Scopus et Web of Science, recherche du 15/11/2026). Le diagramme correspond à la Figure 2 de l'article.

## 1. Nombres d'identification

| Base | Records identifiés |
|---|---|
| Scopus | 118 |
| Web of Science Core Collection | 97 |
| **Total** | **215** |

Formule du tableur : `=SUM(B2:B3)` → 215.

## 2. Distinction entre records, reports et studies

| Notion | Définition | Dans ma SLR |
|---|---|---|
| **Record** | Entrée issue d'une base (titre + résumé) | 215 identifiés, 143 après déduplication |
| **Report** | Document complet associé à un ou plusieurs records | 53 recherchés, 38 évalués, **23 rapports** inclus |
| **Study** | Unité d'analyse finale | **22 études** incluses |

Pourquoi 23 rapports mais 22 études : une étude est décrite dans **deux communications de conférence** du même groupe (mêmes parcelles, même méthode). Les deux rapports ont été **liés et comptés comme une seule étude**. À l'inverse, deux études qui réutilisent les mêmes 24 arbres à des saisons différentes ont été gardées **séparées** (données acquises à des saisons différentes), en signalant qu'elles ne sont pas indépendantes.

## 3. Tableau de vérification

| # | Étape | Nombre | Formule |
|---|---|---|---|
| B2 | Records identifiés | 215 | `=SUM(…)` |
| B3 | Doublons supprimés (70 par DOI, 2 par titre normalisé) | 72 | saisi |
| B4 | Records évalués sur titre et résumé | **143** | `=B2-B3` |
| B5 | Records exclus (titre/résumé) | 90 | saisi |
| B6 | Rapports recherchés | **53** | `=B4-B5` |
| B7 | Rapports non retrouvés | 15 | saisi |
| B8 | Rapports évalués en texte intégral | **38** | `=B6-B7` |
| B9 | Rapports exclus avec motifs | 15 | saisi |
| B10 | Rapports inclus | **23** | `=B8-B9` |
| B11 | Études incluses (deux rapports = une étude) | **22** | `=B10-1` |

Le dernier calcul (`-1`) correspond à l'unique étude décrite dans deux rapports.

## 4. Références après déduplication

```
Records examinés = Records identifiés − Doublons supprimés = 215 − 72 = 143
```
Origine des 143 : 71 indexés dans les deux bases, 46 dans Scopus seul, 26 dans Web of Science seul.

## 5. Screening des titres et résumés

```
Rapports recherchés = Records examinés − Exclus titre/résumé = 143 − 90 = 53
```

| Code | Motif | Nombre |
|---|---|---|
| E2 | Autre culture ou hors sujet | 36 |
| E3 | Pas de cible maladie ou stress | 17 |
| E7 | Livre, chapitre ou front matter | 14 |
| E4 | Pas de capteur aérien ou satellite | 12 |
| E6 | Revue ou éditorial | 11 |
| **Total** | | **90** |

## 6. Recherche des textes intégraux

53 rapports recherchés (accès institutionnel ou dépôts ouverts). **15 non retrouvés**, donc :

```
Rapports évalués = 53 − 15 = 38
```

## 7. Textes non récupérés

Les 15 rapports non retrouvés sont listés dans le Supplementary Material S2 avec leur décision du premier stade : **11 classés « inclure » et 4 « incertain »**. Onze de ces quinze rapports sont des communications de conférence, souvent de groupes déjà présents dans le corpus ; ce type de publication est probablement sous-représenté (limite déclarée). Ils ne reçoivent pas de code d'exclusion : ils sont comptés à part dans le diagramme.

## 8. Éligibilité des textes intégraux

Chaque rapport évalué reçoit une décision et, en cas d'exclusion, **un seul code** (premier critère non rempli).

```
Rapports inclus = Rapports évalués − Exclusions = 38 − 15 = 23 rapports (22 études)
```

## 9. Exclusions avec motifs (texte intégral)

| Code | Motif | Nombre | Études exclues |
|---|---|---|---|
| E4 | Pas d'imagerie aérienne ou satellite | 5 | Beyaz et Ozkaya ; Alrashdi et Abozeid ; Bruno et al. ; Estrada et al. ; Abu-Hammour et al. |
| E5 | Pas de modèle d'apprentissage | 5 | Panagiotopoulou et al. ; Telesca et al. ; Telesca et Lasaponara ; Quille-Mamani et al. ; Navrozidis et al. (2020) |
| E3 | Pas de cible maladie ou stress | 5 | Cilli et al. ; Alfonso et al. ; Vasilakos et Verykios ; Kalo et al. ; Majikumna et al. |
| | **Total** | **15** | |

La raison détaillée de chaque exclusion figure dans le Lab 6 (Table 6 de l'article).

## 10. Nombre final d'études incluses et contrôles

```python
identifies, doublons = 215, 72
exclus_titre, non_retrouves, exclus_texte = 90, 15, 15

examines = identifies - doublons              # 143
recherches = examines - exclus_titre          # 53
evalues = recherches - non_retrouves          # 38
rapports_inclus = evalues - exclus_texte      # 23
etudes = rapports_inclus - 1                  # 22 (un rapport en double pour une étude)

assert (examines, recherches, evalues, rapports_inclus, etudes) == (143, 53, 38, 23, 22)
```

Checklist de cohérence :
- 215 = 72 + 143 ✔
- 143 = 90 + 53 ✔
- 53 = 15 + 38 ✔
- 38 = 15 + 23 ✔
- 23 rapports = 22 études (une étude décrite dans deux rapports) ✔

## 11. Diagramme PRISMA 2020

Valeurs à saisir dans chaque case (outil en ligne officiel PRISMA 2020 ou tout outil de dessin, en respectant la même structure) :

```
IDENTIFICATION
  Records identifiés dans les bases (n = 215)
     Scopus (n = 118) ; Web of Science Core Collection (n = 97)
  Records supprimés avant screening : doublons (n = 72 ; 70 par DOI, 2 par titre normalisé)
          ↓
SCREENING
  Records évalués sur titre et résumé (n = 143)      →  Records exclus (n = 90)
                                                           E2 autre culture/hors sujet (n = 36)
                                                           E3 pas de cible maladie/stress (n = 17)
                                                           E7 livre/chapitre/front matter (n = 14)
                                                           E4 pas de capteur aérien/satellite (n = 12)
                                                           E6 revue/éditorial (n = 11)
          ↓
  Rapports recherchés (n = 53)                       →  Rapports non retrouvés (n = 15)
                                                           (décision au 1er stade : inclure 11, incertain 4)
          ↓
  Rapports évalués pour l'éligibilité (n = 38)       →  Rapports exclus (n = 15)
                                                           E3 (n = 5) ; E4 (n = 5) ; E5 (n = 5)
          ↓
INCLUSION
  Études incluses dans la revue (n = 22)
  Rapports des études incluses (n = 23)
```

La version graphique est la **Figure 2** de l'article. Cases utilisées : « Records identified from databases », « Records removed before screening », « Records screened », « Records excluded », « Reports sought for retrieval », « Reports not retrieved », « Reports assessed for eligibility », « Reports excluded », « Studies included », « Reports of included studies ». Aucune case « autres sources » n'est utilisée : la littérature grise et les listes de références n'ont pas été recherchées.

## 12. Vérification, questions et défis

**Q1. 1200 références identifiées et 300 doublons : combien examinées ?**
1200 − 300 = **900**.

**Q2. 400 exclues au screening, 250 textes recherchés dont 20 non récupérés : combien évalués ?**
Hypothèse : les 250 sont les textes recherchés (la phrase est ambiguë). 250 − 20 = **230** textes évalués. Le chiffre de 400 exclues n'influence pas ce calcul : il sert à déterminer les 250 recherchés (références examinées − 400).

**Q3. Pourquoi les flèches doivent-elles être cohérentes ?**
Chaque nombre d'une case doit être égal au nombre de la case précédente moins ce qui sort sur le côté. Sinon des références « disparaissent » ou sont comptées deux fois, ce qui rend le flux invérifiable et remet en cause la transparence et la reproductibilité.

**Défi 1 : corriger un tableau incohérent.**
Pour 950 identifiées et 200 doublons, les références examinées doivent être 950 − 200 = **750**, et non 800 (erreur de 50). À partir de là, chaque ligne suivante doit être recalculée avec la même règle (recherchés = examinés − exclus titre/résumé, évalués = recherchés − non récupérés, inclus = évalués − exclusions).

**Défi 2 : diagramme à partir des nombres 850, 150, 500, 120, 380, 15, 365, 130, 235.**
- 380 = 500 − 120 ; 365 = 380 − 15 ; 235 = 365 − 130 : la suite **500 → 120 → 380 → 15 → 365 → 130 → 235** est cohérente (500 examinés, 120 exclus au titre/résumé, 380 recherchés, 15 non récupérés, 365 évalués, 130 exclus, 235 inclus).
- En revanche 850 − 150 = 700, et non 500 : **200 références ne sont pas expliquées** entre la déduplication et le screening. Il faut soit trouver l'étape manquante, soit corriger les nombres. Ce point doit être signalé et justifié dans le rendu.

## 13. Résumé

215 records identifiés (Scopus 118, WoS 97), 72 doublons supprimés, 143 évalués sur titre et résumé, 90 exclus, 53 rapports recherchés, 15 non retrouvés, 38 évalués en texte intégral, 15 exclus avec motifs (E3, E4, E5 à 5 chacun), soit **23 rapports et 22 études incluses**. Toutes les relations arithmétiques sont vérifiées et le diagramme est la Figure 2 de l'article.
