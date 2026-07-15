from __future__ import annotations

import calendar
import re
import unicodedata
from dataclasses import dataclass
from datetime import date

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
            # Allemand (forme normalisee sans umlauts)
            "margen", "rendite", "rentabilitat", "gewinn", "gesunken",
            "sinkt", "sinken", "ruckgang", "quartal", "produkt", "produkte", "artikel",
            # Anglais
            "margin", "margins", "profitability", "drop", "drops", "dropped",
            "falling", "declining", "decline", "quarter", "product", "products",
            "item", "items",
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
                WHERE o.order_date >= '{since_date}'
                GROUP BY mois, p.reference
                ORDER BY mois ASC, taux_marge ASC
                LIMIT {top_n}
            """,
            "postgres": """
                SELECT
                  TO_CHAR(o.order_date, 'YYYY-MM') AS mois,
                  p.reference AS produit,
                  ROUND(SUM(o.revenue - o.cost), 2) AS marge,
                  ROUND(100.0 * SUM(o.revenue - o.cost) / NULLIF(SUM(o.revenue), 0), 2) AS taux_marge
                FROM orders o
                JOIN products p ON p.id = o.product_id
                WHERE o.order_date >= DATE '{since_date}'
                GROUP BY TO_CHAR(o.order_date, 'YYYY-MM'), p.reference
                ORDER BY mois ASC, taux_marge ASC
                LIMIT {top_n}
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
            # Allemand
            "engpass", "engpasse", "bestand", "bestande", "reichweite",
            "nachschub", "ausverkauft", "knapp", "tagen", "nachsten",
            # Anglais
            "stockout", "stockouts", "shortage", "shortages", "coverage",
            "replenishment", "runout", "risk", "days", "next",
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
                WHERE o.order_date >= '{since_date}'
                GROUP BY p.id
                HAVING jours_couverture < {horizon_days}
                ORDER BY jours_couverture ASC
                LIMIT {top_n}
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
                WHERE o.order_date >= DATE '{since_date}'
                GROUP BY p.id, p.reference, p.category, p.current_stock, p.safety_stock
                HAVING ROUND(p.current_stock::numeric / GREATEST(1.0, SUM(o.quantity)::numeric / 90.0), 1) < {horizon_days}
                ORDER BY jours_couverture ASC
                LIMIT {top_n}
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
            # Allemand
            "lieferant", "lieferanten", "verspatet", "verspatung", "verspatungen",
            "lieferung", "lieferungen", "lieferzeit", "punktlichkeit", "zuverlassigkeit",
            # Anglais
            "supplier", "suppliers", "late", "delay", "delays", "delivery",
            "deliveries", "punctuality", "reliability",
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
                WHERE sd.delivery_date >= '{since_date}'
                GROUP BY s.id
                ORDER BY retard_moyen_jours DESC
                LIMIT {top_n}
            """,
            "postgres": """
                SELECT
                  s.name AS fournisseur,
                  COUNT(*) AS livraisons,
                  ROUND(AVG(sd.delay_days), 1) AS retard_moyen_jours,
                  SUM(CASE WHEN sd.delay_days > 0 THEN 1 ELSE 0 END) AS livraisons_en_retard
                FROM supplier_delays sd
                JOIN suppliers s ON s.id = sd.supplier_id
                WHERE sd.delivery_date >= DATE '{since_date}'
                GROUP BY s.id, s.name
                ORDER BY retard_moyen_jours DESC
                LIMIT {top_n}
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
            # Allemand
            "produktion", "linie", "linien", "fehler", "ausschuss",
            "qualitat", "effizienz", "fertigung", "defekte", "werk",
            # Anglais
            "line", "lines", "defect", "defects", "quality", "efficiency",
            "yield", "workshop",
        ),
        sql={
            "sqlite": """
                SELECT
                  line AS ligne,
                  SUM(volume) AS volume_produit,
                  SUM(defects) AS defauts,
                  ROUND(100.0 * SUM(defects) / NULLIF(SUM(volume), 0), 2) AS taux_defaut
                FROM production_batches
                WHERE produced_at >= '{since_date}'
                GROUP BY line
                ORDER BY taux_defaut DESC
                LIMIT {top_n}
            """,
            "postgres": """
                SELECT
                  line AS ligne,
                  SUM(volume) AS volume_produit,
                  SUM(defects) AS defauts,
                  ROUND(100.0 * SUM(defects) / NULLIF(SUM(volume), 0), 2) AS taux_defaut
                FROM production_batches
                WHERE produced_at >= DATE '{since_date}'
                GROUP BY line
                ORDER BY taux_defaut DESC
                LIMIT {top_n}
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
            # Allemand
            "umsatz", "umsatze", "erlos", "erlose", "monatlich", "monatliche",
            "kategorie", "kategorien", "verkauf", "verkaufe", "entwicklung",
            # Anglais
            "revenue", "revenues", "sales", "monthly", "category", "categories",
            "turnover",
        ),
        sql={
            "sqlite": """
                SELECT
                  strftime('%Y-%m', o.order_date) AS mois,
                  p.category AS categorie,
                  ROUND(SUM(o.revenue), 2) AS chiffre_affaires
                FROM orders o
                JOIN products p ON p.id = o.product_id
                WHERE o.order_date >= '{since_date}'
                GROUP BY mois, p.category
                ORDER BY mois ASC, chiffre_affaires DESC
                LIMIT {top_n}
            """,
            "postgres": """
                SELECT
                  TO_CHAR(o.order_date, 'YYYY-MM') AS mois,
                  p.category AS categorie,
                  ROUND(SUM(o.revenue), 2) AS chiffre_affaires
                FROM orders o
                JOIN products p ON p.id = o.product_id
                WHERE o.order_date >= DATE '{since_date}'
                GROUP BY TO_CHAR(o.order_date, 'YYYY-MM'), p.category
                ORDER BY mois ASC, chiffre_affaires DESC
                LIMIT {top_n}
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
            # Allemand
            "lager", "ladenhuter", "veraltet", "lange", "liegen",
            "liegt", "bewegung", "alt", "alte",
            # Anglais
            "sitting", "idle", "stale", "ageing", "aging", "long",
            "movement", "obsolete", "unsold",
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
                LIMIT {top_n}
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
                LIMIT {top_n}
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
            # Allemand
            "logistik", "routen", "spediteur", "fracht", "teuer",
            "teurer", "kosten", "versand", "versandkosten",
            # Anglais
            "logistics", "carrier", "carriers", "freight", "expensive",
            "cost", "costs", "shipping", "shipment", "shipments",
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
                WHERE shipped_at >= '{since_date}'
                GROUP BY route, carrier
                ORDER BY cout_moyen DESC
                LIMIT {top_n}
            """,
            "postgres": """
                SELECT
                  route,
                  carrier AS transporteur,
                  ROUND(AVG(cost), 2) AS cout_moyen,
                  ROUND(SUM(cost), 2) AS cout_total,
                  ROUND(AVG(delay_days), 1) AS retard_moyen_jours
                FROM shipments
                WHERE shipped_at >= DATE '{since_date}'
                GROUP BY route, carrier
                ORDER BY cout_moyen DESC
                LIMIT {top_n}
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
            # Allemand
            "retoure", "retouren", "rucksendung", "rucksendungen", "rucklaufe",
            "reklamation", "reklamationen", "grund", "grunde",
            "produkt", "produkte", "artikel",
            # Anglais
            "return", "returns", "rate", "refund", "complaint", "complaints",
            "product", "products", "item", "items",
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
                WHERE r.returned_at >= '{since_date}'
                GROUP BY p.id
                ORDER BY quantite_retournee DESC
                LIMIT {top_n}
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
                WHERE r.returned_at >= DATE '{since_date}'
                GROUP BY p.id, p.reference, p.category
                ORDER BY quantite_retournee DESC
                LIMIT {top_n}
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
            # Allemand
            "kunde", "kunden", "konzentration", "abhangigkeit", "grossten",
            "wichtigsten", "anteil", "umsatzanteil",
            # Anglais
            "customer", "customers", "dependence", "dependency", "largest",
            "biggest", "share",
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
                LIMIT {top_n}
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
                LIMIT {top_n}
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
            # Allemand
            "anomalien", "ungewohnlich", "ungewohnliche", "abweichung",
            "abweichungen", "auffallig", "plotzlich", "verandert", "monat",
            # Anglais
            "anomaly", "anomalies", "unusual", "unusually", "abnormal",
            "deviation", "spike", "sudden", "suddenly", "changed", "month",
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
                LIMIT {top_n}
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
                LIMIT {top_n}
            """,
        },
        chart=ChartSpec(type="bar", x="produit", y="ecart", title="Ecarts du dernier mois"),
        explanation="La requete remonte les plus grands ecarts entre le dernier mois disponible et la moyenne observee.",
    ),
)

EXAMPLE_QUESTIONS = [
    "Quels produits ont vu leur marge baisser le trimestre dernier ?",
    "Quels SKU risquent une rupture dans les 30 prochains jours ?",
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
    # Allemand (forme normalisee)
    r"losche[n]?|loesche[n]?|entferne[n]?|aktualisiere[n]?|"
    r"ersetze[n]?|hinzufugen|einfugen|fuge|"
    # Anglais (verbes naturels + verbes SQL)
    # NB : "drop" est volontairement absent — "margin/sales drop" est une
    # tournure de lecture courante ; un vrai "DROP TABLE" reste bloque par le
    # garde-fou SQL (parseur AST), pas par la detection en langage naturel.
    r"remove[ds]?|erase[ds]?|wipe[ds]?|rename[ds]?|replace[ds]?|"
    r"modif(?:y|ies|ied)|clear[s]?|add[s]?|"
    r"delete|update|insert|truncate|alter"
    r")\b"
)


def is_write_request(question: str) -> bool:
    return bool(_WRITE_REQUEST_PATTERN.search(_normalize(question)))


# ─── Parametres de requete ────────────────────────────────────────────────────

# Fin des donnees de demonstration : ancre des fenetres temporelles relatives.
DEMO_DATA_ANCHOR = date(2026, 6, 30)

TOP_N_BOUNDS = (1, 100)
HORIZON_DAYS_BOUNDS = (1, 365)
WINDOW_MONTHS_BOUNDS = (1, 24)

# Parametres supportes par intention ; les defauts reproduisent exactement
# les valeurs historiques des templates.
PARAM_SPECS: dict[str, dict[str, object]] = {
    "margin_trend": {"top_n": 50, "since_date": "2026-04-01"},
    "stockout_risk": {"top_n": 50, "horizon_days": 30, "since_date": "2026-04-01"},
    "supplier_delays": {"top_n": 50, "since_date": "2026-01-01"},
    "production_efficiency": {"top_n": 50, "since_date": "2026-01-01"},
    "revenue_trend": {"top_n": 80, "since_date": "2026-01-01"},
    "stock_ageing": {"top_n": 50},
    "logistics_cost": {"top_n": 50, "since_date": "2026-01-01"},
    "returns_rate": {"top_n": 50, "since_date": "2026-03-01"},
    "customer_concentration": {"top_n": 50},
    "anomaly_detection": {"top_n": 50},
}


@dataclass(frozen=True)
class QueryParameters:
    top_n: int | None = None
    horizon_days: int | None = None
    window_months: int | None = None


_TOP_N_PATTERN = re.compile(
    r"\btop\s*(\d{1,3})\b"
    r"|\b(\d{1,3})\s+(?:premiers?|principaux|principales|meilleurs?"
    r"|plus\s+(?:gros|grands?|grosses|importants?))\b"
    r"|\b(?:die\s+)?(\d{1,3})\s+(?:grossten|wichtigsten|besten)\b"
    r"|\b(?:the\s+)?(\d{1,3})\s+(?:largest|biggest|leading|top)\b"
)
_HORIZON_PATTERN = re.compile(
    r"\b(\d{1,3})\s*(?:prochains?\s+)?jours?\b"
    r"|\b(\d{1,3})\s+tag(?:e|en)?\b"
    r"|\b(?:next\s+|within\s+|in\s+)?(\d{1,3})\s+days?\b"
)
_WINDOW_PATTERN = re.compile(
    r"\b(\d{1,2})\s*derniers?\s+mois\b"
    r"|\bdepuis\s+(\d{1,2})\s+mois\b"
    r"|\bsur\s+(\d{1,2})\s+mois\b"
    r"|\b(?:letzten\s+)?(\d{1,2})\s+monat(?:e|en)?\b"
    r"|\b(?:last\s+|past\s+|over\s+|in\s+)?(\d{1,2})\s+months?\b"
)


def extract_query_parameters(question: str) -> QueryParameters:
    """Extraction deterministe des parametres exprimes dans la question.

    Chaque valeur est un entier borne ; aucune chaine issue de la question
    n'atteint jamais le SQL.
    """
    normalized = _normalize(question)

    top_n = _first_int(_TOP_N_PATTERN.search(normalized))
    horizon = _first_int(_HORIZON_PATTERN.search(normalized))
    months = _first_int(_WINDOW_PATTERN.search(normalized))
    if months is None:
        if "trimestre" in normalized or "quartal" in normalized or "quarter" in normalized:
            months = 3
        elif (
            "semestre" in normalized
            or "halbjahr" in normalized
            or "semester" in normalized
            or "half year" in normalized
            or "half-year" in normalized
        ):
            months = 6

    return QueryParameters(
        top_n=_clamp(top_n, *TOP_N_BOUNDS),
        horizon_days=_clamp(horizon, *HORIZON_DAYS_BOUNDS),
        window_months=_clamp(months, *WINDOW_MONTHS_BOUNDS),
    )


def render_intent_sql(
    intent: IntentDefinition, dialect: Dialect, params: QueryParameters
) -> tuple[str, list[str]]:
    """Rend le template SQL avec les parametres extraits de la question.

    Retourne le SQL final et la liste des parametres explicitement appliques
    (vide si la question ne precisait rien : les defauts s'appliquent).
    """
    spec = PARAM_SPECS.get(intent.id, {"top_n": 50})
    values: dict[str, object] = dict(spec)
    applied: list[str] = []

    if params.top_n is not None and "top_n" in spec:
        values["top_n"] = params.top_n
        applied.append(f"top {params.top_n}")
    if params.horizon_days is not None and "horizon_days" in spec:
        values["horizon_days"] = params.horizon_days
        applied.append(f"horizon {params.horizon_days} jours")
    if params.window_months is not None and "since_date" in spec:
        since = _months_before(DEMO_DATA_ANCHOR, params.window_months).isoformat()
        values["since_date"] = since
        applied.append(f"fenetre {params.window_months} mois (depuis {since})")

    return intent.sql_for(dialect).format_map(values), applied


def _months_before(anchor: date, months: int) -> date:
    total = anchor.year * 12 + (anchor.month - 1) - months
    year, month = divmod(total, 12)
    month += 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _first_int(match: re.Match[str] | None) -> int | None:
    if match is None:
        return None
    for group in match.groups():
        if group:
            return int(group)
    return None


def _clamp(value: int | None, lower: int, upper: int) -> int | None:
    if value is None:
        return None
    return max(lower, min(upper, value))


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
    decomposed = unicodedata.normalize("NFD", value.lower().replace("ß", "ss"))
    without_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return without_accents
