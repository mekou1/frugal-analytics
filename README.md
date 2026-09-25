# 📖 Le Registre Frugal

> **Micro-SaaS d'Analytics Éthique & Souverain — Style Karpathy**  
> Clone fonctionnel de micro-analytics sans cookie ni bandeau intrusif.  
> Conçu en double aveugle via le **Frugal Vibe Framework**.

---

## 🎯 Principes Fondamentaux

1. **Zéro Mouchard, Zéro Cookie** : Aucun cookie HTTP, aucun `localStorage`, aucun identifiant persistant client-side.
2. **Anonymat Journalier (SHA256)** : L'empreinte visiteur est hachée avec la date du jour et un sel éphémère.
3. **Frugalité Radicale & Zéro NPM** : 100% Python standard library (`http.server`, `sqlite3`), 100% Vanilla HTML/CSS/JS.
4. **Règle des 150 Lignes** : Chaque fichier source fait moins de 120 lignes de code direct et lisible.

---

## 🚀 Démarrage Instantané

```bash
# Lancer le serveur (port 8092 par défaut)
python3 -m core.server
```
Accédez au tableau de bord sur : **http://127.0.0.1:8092**

---

## 📦 Bribe de Suivi à Copier

Ajoutez simplement cette ligne dans le `<head>` de vos pages web :
```html
<script defer data-domain="votre-domaine.com" src="http://127.0.0.1:8092/tracker.js"></script>
```

---

## 🧪 Tests Oracles

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```
