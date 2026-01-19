# Guide d’utilisation — Bécar Ops Controller Cockpit (démo)

## Objectif
Cette application illustre un **cockpit de contrôle opérationnel** :
- KPIs (coût/h, coût/km, coût/m³)
- Rentabilité et variances vs cibles
- Plan d’action (CAPA) avec suivi
- Préparation à un logiciel d’entretien (type **MIR**) : données, contrôles, indicateurs

> Par défaut, les données sont **synthétiques** (démo). Ne pas téléverser de données confidentielles.

## Démarrage rapide
1. Saisir le **mot de passe** (configuré dans Streamlit Secrets ou variable d’environnement).
2. Choisir la **langue** dans la barre latérale.
3. Onglet **1) Données** :
   - soit générer des données synthétiques,
   - soit téléverser un CSV d’opérations (et optionnellement CAPA/MIR).

## Onglets
### 0) Accueil
Vue d’ensemble : KPIs globaux + export d’une **note de service PDF** et d’un **pack ZIP** (données + résultats).

### 1) Données
- Génération synthétique (seed reproductible)
- Téléversement CSV
- Téléchargement de gabarits CSV

### 2) Qualité
Contrôles de qualité (formats, valeurs manquantes, doublons) sur :
- Opérations
- CAPA
- MIR

### 3) Cockpit KPI
Filtres (période / filiale / activité / contrat / équipement) et graphiques :
- Série temporelle du coût/km (hebdomadaire)
- Profit par contrat
- Tableau de recommandations (optimisation d’actifs)

### 4) Variances & rentabilité
Table “scorée” des écarts vs cibles + génération d’actions CAPA à partir des plus gros écarts.

### 5) Plan d’action (CAPA)
Édition et suivi des actions (qui / quoi / quand / statut) + export CSV.

### 6) Préparation MIR
Aperçu des événements d’entretien + KPIs simples maintenance (downtime, coût) + export CSV.

### 7) Scénarios
What-if multi-variables sur les coûts / revenus / volumes, comparaison à la base, et bibliothèque de scénarios exportable.

## Données réelles (optionnel)
Si vous utilisez des données réelles :
- privilégier des extraits **anonymisés** (pas de données nominatives),
- limiter aux champs nécessaires,
- et valider les règles de confidentialité avant tout téléversement.
