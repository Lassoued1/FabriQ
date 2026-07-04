from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .database import Dialect
from .models import ChartSpec


@dataclass(frozen=True)
class IntentDefinition:
    id: str
    label: str
    description: str
    keywords: tuple[str, ...]
    sql: dict[Dialect, str]
    chart: ChartSpec
    explanation: str

    def sql_for(self, dialect: Dialect) -> str:
        return self.sql[dialect]


@dataclass(frozen=True)
class IntentMatch:
    intent: IntentDefinition | None
    score: int
    matched_keywords: tuple[str, ...]


@dataclass(frozen=True)
class IntentCandidate:
    intent: IntentDefinition
    score: int
    matched_keywords: tuple[str, ...]


@dataclass(frozen=True)
class ColumnDefinition:
    name: str
    label: str
    description: str


@dataclass(frozen=True)
class TableDefinition:
    name: str
    label: str
    description: str
    columns: tuple[ColumnDefinition, ...]


TABLE_CATALOG: tuple[TableDefinition, ...] = (
    TableDefinition(
        name="products",
        label="Produits",
        description="Referentiel produit avec categorie, stock courant et seuil de securite.",
        columns=(
            ColumnDefinition("id", "Identifiant produit", "Cle technique du produit."),
            ColumnDefinition("reference", "Reference", "Nom court ou SKU affiche dans les analyses."),
            ColumnDefinition("category", "Categorie", "Famille metier du produit."),
            ColumnDefinition("current_stock", "Stock actuel", "Quantite actuellement disponible."),
            ColumnDefinition("safety_stock", "Stock de securite", "Seuil minimal cible avant risque operationnel."),
        ),
    ),
    TableDefinition(
        name="orders",
        label="Commandes",
        description="Historique des ventes avec quantites, revenus, couts, clients et produits.",
        columns=(
            ColumnDefinition("id", "Identifiant commande", "Cle technique de la commande."),
            ColumnDefinition("order_date", "Date de commande", "Date utilisee pour les tendances mensuelles."),
            ColumnDefinition("product_id", "Produit", "Produit vendu, relie a la table products."),
            ColumnDefinition("customer_id", "Client", "Client acheteur, relie a la table customers."),
            ColumnDefinition("quantity", "Quantite", "Volume vendu sur la commande."),
            ColumnDefinition("revenue", "Revenu", "Chiffre d'affaires de la ligne de commande."),
            ColumnDefinition("cost", "Cout", "Cout associe a la ligne de commande."),
        ),
    ),
    TableDefinition(
        name="suppliers",
        label="Fournisseurs",
        description="Referentiel fournisseur utilise pour qualifier les retards de livraison.",
        columns=(
            ColumnDefinition("id", "Identifiant fournisseur", "Cle technique du fournisseur."),
            ColumnDefinition("name", "Nom fournisseur", "Nom affiche dans les analyses de retard."),
        ),
    ),
    TableDefinition(
        name="supplier_delays",
        label="Retards fournisseurs",
        description="Evenements de livraison avec retard mesure en jours.",
        columns=(
            ColumnDefinition("id", "Identifiant livraison", "Cle technique de l'evenement de livraison."),
            ColumnDefinition("supplier_id", "Fournisseur", "Fournisseur concerne par la livraison."),
            ColumnDefinition("delivery_date", "Date de livraison", "Date effective de livraison."),
            ColumnDefinition("delay_days", "Retard en jours", "Nombre de jours de retard, negatif ou nul si en avance ou a temps."),
        ),
    ),
    TableDefinition(
        name="production_batches",
        label="Lots de production",
        description="Production par ligne avec volume produit et defauts declares.",
        columns=(
            ColumnDefinition("id", "Identifiant lot", "Cle technique du lot de production."),
            ColumnDefinition("line", "Ligne", "Ligne ou atelier de production."),
            ColumnDefinition("produced_at", "Date de production", "Date du lot produit."),
            ColumnDefinition("volume", "Volume produit", "Quantite produite dans le lot."),
            ColumnDefinition("defects", "Defauts", "Nombre d'unites defectueuses ou rebutees."),
        ),
    ),
    TableDefinition(
        name="inventory_movements",
        label="Mouvements de stock",
        description="Historique des mouvements permettant de detecter les stocks dormants.",
        columns=(
            ColumnDefinition("id", "Identifiant mouvement", "Cle technique du mouvement."),
            ColumnDefinition("product_id", "Produit", "Produit concerne par le mouvement."),
            ColumnDefinition("happened_at", "Date du mouvement", "Date du dernier flux connu."),
            ColumnDefinition("quantity_delta", "Variation de stock", "Quantite ajoutee ou retiree du stock."),
        ),
    ),
    TableDefinition(
        name="shipments",
        label="Expeditions",
        description="Expeditions par route et transporteur avec cout et retard logistique.",
        columns=(
            ColumnDefinition("id", "Identifiant expedition", "Cle technique de l'expedition."),
            ColumnDefinition("route", "Route", "Axe logistique analyse."),
            ColumnDefinition("carrier", "Transporteur", "Transporteur utilise."),
            ColumnDefinition("shipped_at", "Date d'expedition", "Date de depart ou d'expedition."),
            ColumnDefinition("cost", "Cout", "Cout logistique de l'expedition."),
            ColumnDefinition("delay_days", "Retard en jours", "Retard logistique observe."),
        ),
    ),
    TableDefinition(
        name="returns",
        label="Retours",
        description="Retours produit avec quantite et motif declare.",
        columns=(
            ColumnDefinition("id", "Identifiant retour", "Cle technique du retour."),
            ColumnDefinition("product_id", "Produit", "Produit retourne."),
            ColumnDefinition("returned_at", "Date retour", "Date de reception du retour."),
            ColumnDefinition("quantity", "Quantite retournee", "Nombre d'unites retournees."),
            ColumnDefinition("reason", "Motif", "Motif principal du retour."),
        ),
    ),
    TableDefinition(
        name="customers",
        label="Clients",
        description="Referentiel client utilise pour mesurer la concentration du chiffre d'affaires.",
        columns=(
            ColumnDefinition("id", "Identifiant client", "Cle technique du client."),
            ColumnDefinition("name", "Nom client", "Nom affiche dans les analyses commerciales."),
        ),
    ),
)


INTENTS: tuple[IntentDefinition, ...] = (
    IntentDefinition(
        id="margin_trend",
        label="Tendance de marge",
        description="Detecte les produits ou articles dont la marge ou la rentabilite se degrade.",
        keywords=(
            "marge", "marges", "rentabilite", "rentable", "profit", "profits",
            "baisser", "baisse", "baissent", "diminuer", "diminue", "erosion",
            "trimestre", "produit", "produits", "article", "articles",
        ),
        sql={
            "sqlite": """
                SELECT
                  strftime('%Y-%m', o.order_date) AS mois,
                  p.reference AS produit,
                  ROUND(SUM(o.revenue - o.cost), 2) AS marge,
                  ROUND(100.0 * SUM(o.revenue - o.cost) / NULLIF(SUM(o.revenue), 0), 2) AS taux_marge
                FROM orders o
                JOIN products p ON p.id = o.product_id
                WHERE o.order_date >= '2026-04-01'
                GROUP BY mois, p.reference
                ORDER BY mois ASC, taux_marge ASC
                LIMIT 50
            """,
            "postgres": """
                SELECT
                  TO_CHAR(o.order_date, 'YYYY-MM') AS mois,
                  p.reference AS produit,
                  ROUND(SUM(o.revenue - o.cost), 2) AS marge,
                  ROUND(100.0 * SUM(o.revenue - o.cost) / NULLIF(SUM(o.revenue), 0), 2) AS taux_marge
                FROM orders o
                JOIN products p ON p.id = o.product_id
                WHERE o.order_date >= DATE '2026-04-01'
                GROUP BY TO_CHAR(o.order_date, 'YYYY-MM'), p.reference
                ORDER BY mois ASC, taux_marge ASC
                LIMIT 50
            """,
        },
        chart=ChartSpec(type="line", x="mois", y="taux_marge", title="Evolution du taux de marge"),
        explanation="La requete agrege revenus et couts par mois et produit sur le dernier trimestre disponible.",
    ),
    IntentDefinition(
        id="stockout_risk",
        label="Risque de rupture",
        description="Priorise les SKU et produits qui risquent de manquer selon stock et demande recente.",
        keywords=(
            "rupture", "ruptures", "sku", "stock", "stocks", "couverture",
            "prochains", "jours", "manquer", "manque", "disponibilite",
            "penurie", "reapprovisionnement", "reappro",
        ),
        sql={
            "sqlite": """
                SELECT
                  p.reference AS produit,
                  p.category AS categorie,
                  p.current_stock AS stock_actuel,
                  p.safety_stock AS stock_securite,
                  ROUND(p.current_stock / MAX(1.0, SUM(o.quantity) / 90.0), 1) AS jours_couverture
                FROM products p
                JOIN orders o ON o.product_id = p.id
                WHERE o.order_date >= '2026-04-01'
                GROUP BY p.id
                HAVING jours_couverture < 30
                ORDER BY jours_couverture ASC
                LIMIT 50
            """,
            "postgres": """
                SELECT
                  p.reference AS produit,
                  p.category AS categorie,
                  p.current_stock AS stock_actuel,
                  p.safety_stock AS stock_securite,
                  ROUND(p.current_stock::numeric / GREATEST(1.0, SUM(o.quantity)::numeric / 90.0), 1) AS jours_couverture
                FROM products p
                JOIN orders o ON o.product_id = p.id
                WHERE o.order_date >= DATE '2026-04-01'
                GROUP BY p.id, p.reference, p.category, p.current_stock, p.safety_stock
                HAVING ROUND(p.current_stock::numeric / GREATEST(1.0, SUM(o.quantity)::numeric / 90.0), 1) < 30
                ORDER BY jours_couverture ASC
                LIMIT 50
            """,
        },
        chart=ChartSpec(type="bar", x="produit", y="jours_couverture", title="Jours de couverture par produit"),
        explanation="Le risque est estime avec le stock actuel divise par la demande moyenne quotidienne recente.",
    ),
    IntentDefinition(
        id="supplier_delays",
        label="Retards fournisseurs",
        description="Compare les fournisseurs selon retards, delais et fiabilite de livraison.",
        keywords=(
            "fournisseur", "fournisseurs", "retard", "retards", "ponctualite",
            "livraison", "livraisons", "livrer", "livrent", "delai", "delais",
            "retardataire", "retardataires", "fiabilite",
        ),
        sql={
            "sqlite": """
                SELECT
                  s.name AS fournisseur,
                  COUNT(*) AS livraisons,
                  ROUND(AVG(sd.delay_days), 1) AS retard_moyen_jours,
                  SUM(CASE WHEN sd.delay_days > 0 THEN 1 ELSE 0 END) AS livraisons_en_retard
                FROM supplier_delays sd
                JOIN suppliers s ON s.id = sd.supplier_id
                WHERE sd.delivery_date >= '2026-01-01'
                GROUP BY s.id
                ORDER BY retard_moyen_jours DESC
                LIMIT 50
            """,
            "postgres": """
                SELECT
                  s.name AS fournisseur,
                  COUNT(*) AS livraisons,
                  ROUND(AVG(sd.delay_days), 1) AS retard_moyen_jours,
                  SUM(CASE WHEN sd.delay_days > 0 THEN 1 ELSE 0 END) AS livraisons_en_retard
                FROM supplier_delays sd
                JOIN suppliers s ON s.id = sd.supplier_id
                WHERE sd.delivery_date >= DATE '2026-01-01'
                GROUP BY s.id, s.name
                ORDER BY retard_moyen_jours DESC
                LIMIT 50
            """,
        },
        chart=ChartSpec(type="bar", x="fournisseur", y="retard_moyen_jours", title="Retard moyen fournisseur"),
        explanation="La requete compare les delais moyens et le volume de livraisons en retard par fournisseur.",
    ),
    IntentDefinition(
        id="production_efficiency",
        label="Efficacite production",
        description="Analyse la performance atelier par ligne, volume, defauts, rebuts et rendement.",
        keywords=(
            "production", "ligne", "lignes", "defaut", "defauts", "defectueux",
            "efficacite", "qualite", "rendement", "rebuts", "atelier",
            "ateliers", "productivite", "scrap",
        ),
        sql={
            "sqlite": """
                SELECT
                  line AS ligne,
                  SUM(volume) AS volume_produit,
                  SUM(defects) AS defauts,
                  ROUND(100.0 * SUM(defects) / NULLIF(SUM(volume), 0), 2) AS taux_defaut
                FROM production_batches
                WHERE produced_at >= '2026-01-01'
                GROUP BY line
                ORDER BY taux_defaut DESC
                LIMIT 50
            """,
            "postgres": """
                SELECT
                  line AS ligne,
                  SUM(volume) AS volume_produit,
                  SUM(defects) AS defauts,
                  ROUND(100.0 * SUM(defects) / NULLIF(SUM(volume), 0), 2) AS taux_defaut
                FROM production_batches
                WHERE produced_at >= DATE '2026-01-01'
                GROUP BY line
                ORDER BY taux_defaut DESC
                LIMIT 50
            """,
        },
        chart=ChartSpec(type="bar", x="ligne", y="taux_defaut", title="Taux de defaut par ligne"),
        explanation="Le taux de defaut est calcule par ligne a partir des volumes produits et des defauts declares.",
    ),
    IntentDefinition(
        id="revenue_trend",
        label="Tendance de chiffre d'affaires",
        description="Suit l'evolution des ventes, revenus ou chiffre d'affaires par mois et categorie.",
        keywords=(
            "chiffre", "affaires", "ca", "mensuel", "mensuelle", "mensuelles",
            "mois", "categorie", "categories", "famille", "vente", "ventes",
            "revenu", "revenus", "evolution", "commercial", "facturation",
        ),
        sql={
            "sqlite": """
                SELECT
                  strftime('%Y-%m', o.order_date) AS mois,
                  p.category AS categorie,
                  ROUND(SUM(o.revenue), 2) AS chiffre_affaires
                FROM orders o
                JOIN products p ON p.id = o.product_id
                WHERE o.order_date >= '2026-01-01'
                GROUP BY mois, p.category
                ORDER BY mois ASC, chiffre_affaires DESC
                LIMIT 80
            """,
            "postgres": """
                SELECT
                  TO_CHAR(o.order_date, 'YYYY-MM') AS mois,
                  p.category AS categorie,
                  ROUND(SUM(o.revenue), 2) AS chiffre_affaires
                FROM orders o
                JOIN products p ON p.id = o.product_id
                WHERE o.order_date >= DATE '2026-01-01'
                GROUP BY TO_CHAR(o.order_date, 'YYYY-MM'), p.category
                ORDER BY mois ASC, chiffre_affaires DESC
                LIMIT 80
            """,
        },
        chart=ChartSpec(type="line", x="mois", y="chiffre_affaires", title="Chiffre d'affaires mensuel"),
        explanation="La requete suit le chiffre d'affaires mensuel par categorie de produit.",
    ),
    IntentDefinition(
        id="stock_ageing",
        label="Vieillissement de stock",
        description="Identifie les stocks dormants ou anciens sans mouvement recent.",
        keywords=(
            "vieillissement", "stock", "stocks", "longtemps", "dormant",
            "dormants", "ancien", "anciens", "restes", "immobile", "rotation",
            "mouvement", "mouvements", "obsolescence",
        ),
        sql={
            "sqlite": """
                SELECT
                  p.reference AS produit,
                  p.category AS categorie,
                  p.current_stock AS stock_actuel,
                  MAX(im.happened_at) AS dernier_mouvement,
                  ROUND(julianday('2026-06-30') - julianday(MAX(im.happened_at)), 0) AS jours_sans_mouvement
                FROM products p
                JOIN inventory_movements im ON im.product_id = p.id
                GROUP BY p.id
                ORDER BY jours_sans_mouvement DESC
                LIMIT 50
            """,
            "postgres": """
                SELECT
                  p.reference AS produit,
                  p.category AS categorie,
                  p.current_stock AS stock_actuel,
                  MAX(im.happened_at) AS dernier_mouvement,
                  DATE '2026-06-30' - MAX(im.happened_at) AS jours_sans_mouvement
                FROM products p
                JOIN inventory_movements im ON im.product_id = p.id
                GROUP BY p.id, p.reference, p.category, p.current_stock
                ORDER BY jours_sans_mouvement DESC
                LIMIT 50
            """,
        },
        chart=ChartSpec(type="bar", x="produit", y="jours_sans_mouvement", title="Age du stock"),
        explanation="Le vieillissement est estime par la date du dernier mouvement de stock connu.",
    ),
    IntentDefinition(
        id="logistics_cost",
        label="Cout logistique",
        description="Compare les routes, transporteurs et expeditions selon les couts logistiques.",
        keywords=(
            "logistique", "route", "routes", "transport", "transporteur",
            "transporteurs", "cher", "chers", "cheres", "coute", "coutent",
            "couteuses", "cout", "couts", "frais", "expedition", "expeditions",
        ),
        sql={
            "sqlite": """
                SELECT
                  route,
                  carrier AS transporteur,
                  ROUND(AVG(cost), 2) AS cout_moyen,
                  ROUND(SUM(cost), 2) AS cout_total,
                  ROUND(AVG(delay_days), 1) AS retard_moyen_jours
                FROM shipments
                WHERE shipped_at >= '2026-01-01'
                GROUP BY route, carrier
                ORDER BY cout_moyen DESC
                LIMIT 50
            """,
            "postgres": """
                SELECT
                  route,
                  carrier AS transporteur,
                  ROUND(AVG(cost), 2) AS cout_moyen,
                  ROUND(SUM(cost), 2) AS cout_total,
                  ROUND(AVG(delay_days), 1) AS retard_moyen_jours
                FROM shipments
                WHERE shipped_at >= DATE '2026-01-01'
                GROUP BY route, carrier
                ORDER BY cout_moyen DESC
                LIMIT 50
            """,
        },
        chart=ChartSpec(type="bar", x="route", y="cout_moyen", title="Cout moyen par route"),
        explanation="La requete compare le cout moyen de transport par route et transporteur.",
    ),
    IntentDefinition(
        id="returns_rate",
        label="Retours",
        description="Classe les produits ou articles selon volumes de retours, motifs et reclamations.",
        keywords=(
            "retour", "retours", "taux", "produit", "produits", "article",
            "articles", "qualite", "motif", "motifs", "sav", "defectueux",
            "remboursement", "reclamation", "reclamations",
        ),
        sql={
            "sqlite": """
                SELECT
                  p.reference AS produit,
                  p.category AS categorie,
                  SUM(r.quantity) AS quantite_retournee,
                  COUNT(*) AS retours,
                  GROUP_CONCAT(DISTINCT r.reason) AS motifs
                FROM returns r
                JOIN products p ON p.id = r.product_id
                WHERE r.returned_at >= '2026-03-01'
                GROUP BY p.id
                ORDER BY quantite_retournee DESC
                LIMIT 50
            """,
            "postgres": """
                SELECT
                  p.reference AS produit,
                  p.category AS categorie,
                  SUM(r.quantity) AS quantite_retournee,
                  COUNT(*) AS retours,
                  STRING_AGG(DISTINCT r.reason, ', ') AS motifs
                FROM returns r
                JOIN products p ON p.id = r.product_id
                WHERE r.returned_at >= DATE '2026-03-01'
                GROUP BY p.id, p.reference, p.category
                ORDER BY quantite_retournee DESC
                LIMIT 50
            """,
        },
        chart=ChartSpec(type="bar", x="produit", y="quantite_retournee", title="Retours par produit"),
        explanation="La requete regroupe les retours par produit avec quantite et motifs observes.",
    ),
    IntentDefinition(
        id="customer_concentration",
        label="Concentration clients",
        description="Mesure la dependance au chiffre d'affaires des principaux clients.",
        keywords=(
            "client", "clients", "essentiel", "concentration", "concentrent",
            "representent", "dependance", "risque", "ca", "chiffre", "top",
            "principaux", "gros",
        ),
        sql={
            "sqlite": """
                SELECT
                  c.name AS client,
                  ROUND(SUM(o.revenue), 2) AS chiffre_affaires,
                  ROUND(100.0 * SUM(o.revenue) / (SELECT SUM(revenue) FROM orders), 2) AS part_ca
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                GROUP BY c.id
                ORDER BY chiffre_affaires DESC
                LIMIT 50
            """,
            "postgres": """
                SELECT
                  c.name AS client,
                  ROUND(SUM(o.revenue), 2) AS chiffre_affaires,
                  ROUND(100.0 * SUM(o.revenue) / (SELECT SUM(revenue) FROM orders), 2) AS part_ca
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                GROUP BY c.id, c.name
                ORDER BY chiffre_affaires DESC
                LIMIT 50
            """,
        },
        chart=ChartSpec(type="bar", x="client", y="part_ca", title="Part du CA par client"),
        explanation="La concentration est calculee comme part du chiffre d'affaires total par client.",
    ),
    IntentDefinition(
        id="anomaly_detection",
        label="Detection d'anomalie",
        description="Remonte les variations inhabituelles ou ecarts forts sur le dernier mois disponible.",
        keywords=(
            "anomalie", "anomalies", "anormal", "anormaux", "change",
            "changement", "ecart", "ecarts", "dernier", "mois", "inhabituel",
            "inhabituelle", "variation", "variations", "surprise", "brusque",
        ),
        sql={
            "sqlite": """
                SELECT
                  p.reference AS produit,
                  ROUND(SUM(CASE WHEN strftime('%Y-%m', o.order_date) = '2026-06' THEN o.revenue ELSE 0 END), 2) AS ca_dernier_mois,
                  ROUND(AVG(o.revenue), 2) AS ca_moyen_commande,
                  ROUND(SUM(CASE WHEN strftime('%Y-%m', o.order_date) = '2026-06' THEN o.revenue ELSE 0 END) - AVG(o.revenue), 2) AS ecart
                FROM orders o
                JOIN products p ON p.id = o.product_id
                GROUP BY p.id
                ORDER BY ABS(ecart) DESC
                LIMIT 50
            """,
            "postgres": """
                SELECT
                  p.reference AS produit,
                  ROUND(SUM(CASE WHEN TO_CHAR(o.order_date, 'YYYY-MM') = '2026-06' THEN o.revenue ELSE 0 END), 2) AS ca_dernier_mois,
                  ROUND(AVG(o.revenue), 2) AS ca_moyen_commande,
                  ROUND(SUM(CASE WHEN TO_CHAR(o.order_date, 'YYYY-MM') = '2026-06' THEN o.revenue ELSE 0 END) - AVG(o.revenue), 2) AS ecart
                FROM orders o
                JOIN products p ON p.id = o.product_id
                GROUP BY p.id, p.reference
                ORDER BY ABS(ROUND(SUM(CASE WHEN TO_CHAR(o.order_date, 'YYYY-MM') = '2026-06' THEN o.revenue ELSE 0 END) - AVG(o.revenue), 2)) DESC
                LIMIT 50
            """,
        },
        chart=ChartSpec(type="bar", x="produit", y="ecart", title="Ecarts du dernier mois"),
        explanation="La requete remonte les plus grands ecarts entre le dernier mois disponible et la moyenne observee.",
    ),
)

EXAMPLE_QUESTIONS = [
    "Quels produits ont vu leur marge baisser le trimestre dernier ?",
    "Quels SKU risquent une rupture dans les 14 prochains jours ?",
    "Quels fournisseurs ont ete le plus souvent en retard ?",
    "Quelles lignes de production ont eu le plus de defauts ?",
    "Montre le chiffre d'affaires mensuel par categorie.",
    "Quels produits sont restes trop longtemps en stock ?",
    "Quelles routes sont devenues plus cheres ?",
    "Quels produits ont le taux de retour le plus eleve ?",
    "Quels clients representent l'essentiel du CA ?",
    "Qu'est-ce qui a change anormalement le mois dernier ?",
]

EXAMPLE_BY_INTENT_ID = {
    intent.id: question for intent, question in zip(INTENTS, EXAMPLE_QUESTIONS, strict=True)
}


def semantic_catalog() -> dict[str, object]:
    return {
        "intents": [
            {
                "id": intent.id,
                "label": intent.label,
                "description": intent.description,
                "keywords": list(intent.keywords),
                "example_question": EXAMPLE_BY_INTENT_ID[intent.id],
                "chart": intent.chart.model_dump(),
            }
            for intent in INTENTS
        ],
        "tables": [
            {
                "name": table.name,
                "label": table.label,
                "description": table.description,
                "columns": [
                    {
                        "name": column.name,
                        "label": column.label,
                        "description": column.description,
                    }
                    for column in table.columns
                ],
            }
            for table in TABLE_CATALOG
        ],
    }


# Verbes exprimant une intention d'ecriture : la seule reponse valide est une
# clarification, jamais une analyse (meme en lecture seule, ce serait trompeur).
_WRITE_REQUEST_PATTERN = re.compile(
    r"\b("
    r"supprime[rsz]?|efface[rsz]?|vide[rsz]?|modifie[rsz]?|remplace[rsz]?|"
    r"ajoute[rsz]?|insere[rsz]?|renomme[rsz]?|detrui[st]|detruire|"
    r"mets? a jour|mise a jour|"
    r"drop|delete|update|insert|truncate|alter"
    r")\b"
)


def is_write_request(question: str) -> bool:
    return bool(_WRITE_REQUEST_PATTERN.search(_normalize(question)))


def select_intent(question: str) -> IntentDefinition | None:
    return select_intent_match(question).intent


def _effective_keyword_count(keywords: tuple[str, ...]) -> int:
    """Nombre de mots-cles reellement distincts.

    'produit' et 'produits' matchent tous deux la meme occurrence : un
    mot-cle inclus dans un autre mot-cle matche ne compte pas.
    """
    return sum(
        1
        for keyword in keywords
        if not any(keyword != other and keyword in other for other in keywords)
    )


def select_intent_match(question: str) -> IntentMatch:
    if is_write_request(question):
        return IntentMatch(intent=None, score=0, matched_keywords=())

    candidates = rank_intent_candidates(question)
    if not candidates:
        return IntentMatch(intent=None, score=0, matched_keywords=())

    best_candidate = candidates[0]
    if _effective_keyword_count(best_candidate.matched_keywords) >= 2 and best_candidate.score >= 4:
        return IntentMatch(
            intent=best_candidate.intent,
            score=best_candidate.score,
            matched_keywords=best_candidate.matched_keywords,
        )

    return IntentMatch(
        intent=None,
        score=best_candidate.score,
        matched_keywords=best_candidate.matched_keywords,
    )


def rank_intent_candidates(question: str) -> list[IntentCandidate]:
    normalized_question = _normalize(question)
    tokens = set(re.findall(r"[a-z0-9]+", normalized_question))
    candidates: list[IntentCandidate] = []

    for intent in INTENTS:
        matched_keywords = {keyword for keyword in intent.keywords if keyword in normalized_question}
        score = len(matched_keywords) * 2
        score += sum(1 for keyword in intent.keywords if keyword in tokens)
        if score > 0:
            candidates.append(
                IntentCandidate(
                    intent=intent,
                    score=score,
                    matched_keywords=tuple(sorted(matched_keywords)),
                )
            )

    return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)


def intent_by_id(intent_id: str) -> IntentDefinition | None:
    return next((intent for intent in INTENTS if intent.id == intent_id), None)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    without_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return without_accents
