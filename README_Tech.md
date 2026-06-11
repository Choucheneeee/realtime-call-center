
# 🤖 Assistant Vocal IA – Guide Technique (Realtime Call Center Accelerator)

## 📌 Table des matières
1. [Architecture générale](#architecture)
2. [Structure des fichiers](#structure)
3. [Installation et déploiement](#deploiement)
4. [Configuration](#configuration)
5. [Démarrage et arrêt](#demarrage)
6. [Erreurs fréquentes et solutions](#erreurs)
7. [Personnalisation](#personnalisation)
8. [Annexes (variables d’environnement)](#annexes)

---

## 1. Architecture générale <a name="architecture"></a>

```
[Utilisateur]  →  Navigateur Web / Téléphone
         │
         ├── (WebRTC) → WebSocket → [Application FastAPI / aiohttp]
         │                                 │
         └── (Appel téléphonique) → [Azure Communication Services (ACS)]
                                           │
                                           └── (Direct Routing) → [Votre SBC (Asterisk/FreeSWITCH)] → Opérateur VoIP
```

- **Front‑end** : `index.html`, `app.js`, `style.css` (interface de conversation vocale).
- **Backend** : `app.py` (serveur aiohttp) + modules `backend/` (ACS, OpenAI Realtime, outils).
- **Infrastructure** : Docker, Azure ACS, Azure OpenAI (gpt-realtime), Azure Blob Storage (prompt), Nginx (HTTPS), Let's Encrypt.

---

## 2. Structure des fichiers <a name="structure"></a>

```bash
realtime-call-center-accelerator/
├── README.md                 # ce fichier (votre documentation)
├── CHANGELOG.md
├── LICENSE.md
├── SECURITY.md
├── azure.yaml                # configuration pour `azd` (Azure Developer CLI)
├── system_prompt.md          # prompt par défaut (fallback local)
├── assets/                   # images, logos
├── azd-hooks/                # scripts post‑déploiement
├── data/                     # données (ex: documents RAG)
├── infra/                    # templates Bicep (infrastructure Azure)
├── scripts/                  # utilitaires
└── src/                      # code source principal
    └── app/
        ├── Dockerfile        # construction de l’image Docker
        ├── requirements.txt  # dépendances Python
        ├── app.py            # serveur aiohttp (point d’entrée)
        ├── backend/          # modules métier
        │   ├── acs.py        # gestion des appels ACS (inbound/outbound)
        │   ├── rtmt.py       # WebSocket vers OpenAI Realtime
        │   ├── azure.py      # credentials Azure, stockage blob
        │   ├── helpers.py    # transformation de messages
        │   └── tools/        # fonctions appelables par l’IA (ex: recherche médecin)
        └── static/           # fichiers statiques
            ├── index.html    # interface utilisateur (page d’accueil)
            ├── app.js        # logique WebRTC + appels téléphoniques
            ├── style.css     # styles (ou intégrés dans index.html)
            └── logo-wic-new.png
```

---

## 3. Installation et déploiement <a name="deploiement"></a>

### 3.1 Prérequis
- VM Ubuntu 22.04 (Azure recommandée) avec Docker et Nginx.
- Compte Azure avec les services :
  - Communication Services (ACS) + numéro de téléphone.
  - OpenAI (modèle `gpt-realtime` déployé).
  - Storage Account (blob pour le prompt `system_prompt.md`).
- Domaine public (ex: `callcenter.wic-talk.com`) pointant vers l’IP de la VM.

### 3.2 Construction de l’image Docker
```bash
cd /var/www/realtime-call-center-accelerator/src/app
docker build -t my-callcenter-app .
```

### 3.3 Lancement du conteneur (variables d’environnement)
```bash
CONN_STR=$(az storage account show-connection-string ...)
OPENAI_KEY=$(az cognitiveservices account keys list ...)
ACS_CONN=$(az communication list-key ...)

docker run -d \
  --name callcenter-app \
  --restart unless-stopped \
  -p 8000:8000 \
  -e ACS_CONNECTION_STRING="$ACS_CONN" \
  -e ACS_SOURCE_NUMBER="+33801150807" \
  -e AZURE_OPENAI_ENDPOINT="https://..." \
  -e AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME="gpt-realtime" \
  -e AZURE_OPENAI_API_KEY="$OPENAI_KEY" \
  -e ACS_CALLBACK_PATH="https://callcenter.wic-talk.com/acs/incoming" \
  -e ACS_MEDIA_STREAMING_WEBSOCKET_PATH="wss://callcenter.wic-talk.com/realtime-acs" \
  -e AZURE_STORAGE_CONNECTION_STRING="$CONN_STR" \
  -e BOT_NAME="Aziz" \
  -e COMPANY_NAME="Wic Doctor" \
  -e AZURE_SPEECH_LANGUAGE="fr-FR" \
  -e OPENAI_REALTIME_VOICE="fable" \
  my-callcenter-app
```

### 3.4 Correction de l’erreur `DefaultAzureCredential`
Le conteneur échoue parfois car il tente d’obtenir un token Azure. Désactivez l’appel à `get_token` :
```bash
docker exec callcenter-app sed -i 's/credentials.get_token/# credentials.get_token/' /app/backend/azure.py
docker restart callcenter-app
```

### 3.5 Configuration Nginx (HTTPS)
- Installez Nginx et Let’s Encrypt.
- Créez un fichier de configuration `/etc/nginx/sites-available/callcenter` (proxy vers `localhost:8000`).
- Appliquez le certificat SSL.

---

## 4. Configuration <a name="configuration"></a>

### 4.1 Variables d’environnement essentielles (dans `docker run`)

| Variable | Description | Exemple |
|----------|-------------|---------|
| `ACS_CONNECTION_STRING` | Chaîne de connexion ACS | `endpoint=...;accesskey=...` |
| `ACS_SOURCE_NUMBER` | Numéro source (affiché à l’appelant) | `+33801150807` |
| `AZURE_OPENAI_ENDPOINT` | Endpoint Azure OpenAI (gpt-realtime) | `https://cog-....openai.azure.com/` |
| `AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME` | Nom du déploiement Realtime | `gpt-realtime` |
| `AZURE_OPENAI_API_KEY` | Clé API OpenAI | – |
| `ACS_CALLBACK_PATH` | URL de callback pour les événements ACS | `https://.../acs/incoming` |
| `ACS_MEDIA_STREAMING_WEBSOCKET_PATH` | WebSocket pour le flux audio | `wss://.../realtime-acs` |
| `AZURE_STORAGE_CONNECTION_STRING` | Connexion au stockage blob (prompt personnalisé) | – |
| `AZURE_SPEECH_LANGUAGE` | Langue de synthèse vocale (secours) | `fr-FR` |
| `OPENAI_REALTIME_VOICE` | Voix par défaut | `fable` |
| `BOT_NAME` / `COMPANY_NAME` | Nom du bot (utilisé dans le prompt) | `Aziz`, `Wic Doctor` |

### 4.2 Prompt système personnalisé (`system_prompt.md`)
- Déposez le fichier dans le conteneur **`prompt`** de votre Storage Account.
- Le code le récupère à l’adresse `container_name='prompt'`, `file_name='system_prompt.md'`.
- Exemple de contenu :
  ```markdown
  Vous êtes un assistant IA nommé **Sage** travaillant pour **Wic Doctor**.
  Vous êtes serviable et parlez français.
  ```

### 4.3 Numéro de téléphone et Direct Routing
- Configurez un SBC (Asterisk, FreeSWITCH, Kamailio) pour enregistrer votre trunk VoIP.
- Ajoutez le SBC dans ACS (Direct Routing) avec l’IP publique de votre VM, port 5060 (UDP).
- Créez une voix de route (`.*`) associée au SBC.

---

## 5. Démarrage et arrêt <a name="demarrage"></a>

- **Démarrer** : `docker start callcenter-app`
- **Arrêter** : `docker stop callcenter-app`
- **Redémarrer** : `docker restart callcenter-app`
- **Logs** : `docker logs -f callcenter-app`
- **Entrer dans le conteneur** : `docker exec -it callcenter-app bash` (si bash installé)

---

## 6. Erreurs fréquentes et solutions <a name="erreurs"></a>

| Erreur | Cause probable | Solution |
|--------|----------------|----------|
| `LLM connection or authentication error` | Variables OpenAI manquantes ou incorrectes | Vérifiez `AZURE_OPENAI_ENDPOINT`, `_COMPLETION_DEPLOYMENT_NAME`, `_API_KEY` |
| `DefaultAzureCredential failed` | Appel à `get_token()` dans `azure.py` | Exécutez `sed ...` pour commenter la ligne |
| `User is not entitled to call this destination` (580040) | Le numéro source n’a pas la capacité "Outbound calling" | Utilisez un numéro géographique (pas un numéro gratuit) ou activez l’appel sortant |
| `KeyError: 'number'` (500 Internal Server Error) | Le frontend envoie `phoneNumber` mais le code attend `number` | Modifiez `app.py` pour accepter `phoneNumber` (voir section 7) |
| `WebSocket connection closed` | Problème de réseau ou de certificat TLS | Vérifiez Nginx et le reverse proxy WebSocket |
| `Could not fetch system prompt from Azure Storage` | Mauvais nom de conteneur (`prompt` vs `prompts`) | Utilisez `prompt` (singulier) comme dans le code |
| `502 Bad Gateway` (Nginx) | Conteneur non démarré ou non joignable sur port 8000 | Redémarrez le conteneur et vérifiez `curl localhost:8000` |
| `Timeout` dans les appels sortants | SBC non configuré ou pare-feu bloquant UDP 5060 | Installez Asterisk (section 6.1) et ouvrez les ports |



---

## 7. Personnalisation <a name="personnalisation"></a>

### 7.1 Modifier l’interface web (`index.html`)
- Éditez `src/app/static/index.html` (ou remplacez-le).
- Reconstruisez l’image Docker :
  ```bash
  cd /var/www/realtime-call-center-accelerator/src/app
  docker build -t my-callcenter-app .
  docker stop callcenter-app && docker rm callcenter-app
  # relancez avec les mêmes variables d’environnement
  ```

### 7.2 Ajouter des outils (function calling)
- Créez une fonction dans `backend/tools/` et enregistrez‑la dans `app.py` via `rtmt.tools["nom"] = Tool(...)`.

### 7.3 Changer la voix (OpenAI Realtime)
- Utilisez l’interface web (Config → Voice) ou envoyez une requête `POST /update-voice` avec `{"voice":"coral"}`.

---

## 8. Annexes (variables d’environnement) <a name="annexes"></a>

| Nom | Requis | Défaut | Description |
|-----|--------|--------|-------------|
| `ACS_CONNECTION_STRING` | Oui | – | Chaîne de connexion ACS (clé primaire) |
| `ACS_SOURCE_NUMBER` | Oui | – | Numéro d’appelant (format E.164) |
| `AZURE_OPENAI_ENDPOINT` | Oui | – | Endpoint OpenAI (ex: `https://...openai.azure.com/`) |
| `AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME` | Oui | – | Nom du déploiement Realtime (ex: `gpt-realtime`) |
| `AZURE_OPENAI_API_KEY` | Oui | – | Clé API OpenAI |
| `ACS_CALLBACK_PATH` | Oui | – | URL pour les événements ACS (`/acs/incoming`) |
| `ACS_MEDIA_STREAMING_WEBSOCKET_PATH` | Oui | – | WebSocket pour le média ACS |
| `AZURE_STORAGE_CONNECTION_STRING` | Non | – | Pour le prompt personnalisé |
| `AZURE_SEARCH_ENDPOINT` etc. | Non | – | Pour la recherche RAG |
| `BOT_NAME` | Non | – | Nom du bot (affiché dans le prompt) |
| `COMPANY_NAME` | Non | – | Nom de la société |
| `AZURE_SPEECH_LANGUAGE` | Non | `en-US` | Langue pour TTS (fallback) |
| `OPENAI_REALTIME_VOICE` | Non | `alloy` | Voix par défaut (alloy, echo, fable…) |
