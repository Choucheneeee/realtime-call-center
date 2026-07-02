import aiohttp
import logging
from typing import Any
from backend.tools.tools import Tool, ToolResult, ToolResultDirection

logger = logging.getLogger("voicerag")

_doctor_search_schema = {
    "type": "function",
    "name": "search_doctors",
    "description": "Recherche des médecins selon spécialité, ville, gouvernorat, langue, ou par nom (recherche libre). Retourne une liste de médecins avec leurs coordonnées et un identifiant aléatoire (aleatoire) pour obtenir plus de détails.",
    "parameters": {
        "type": "object",
        "properties": {
            "specialite": {"type": "string", "description": "Spécialité médicale (ex: cardiologue, dentiste)"},
            "ville": {"type": "string", "description": "Ville du médecin"},
            "gouvernorat": {"type": "string", "description": "Gouvernorat (ex: Nabeul, Tunis)"},
            "langue": {"type": "string", "description": "Langue parlée (ex: Français, Anglais)"},
            "search": {"type": "string", "description": "Recherche libre par nom du médecin, spécialité ou ville (ex: 'Saad Gharnatei', 'cardiologue Nabeul')"},
            "query": {"type": "string", "description": "Alias pour 'search' (compatibilité)"},
            "type_doctor": {"type": "string", "enum": ["conventionné", "non-conventionné"]},
            "genre": {"type": "string", "enum": ["homme", "femme"]},
            "en_ligne": {"type": "boolean", "description": "Consultation en ligne disponible"}
        },
        "required": []
    }
}

async def _search_doctors_tool(args: Any) -> ToolResult:
    print(f"🔍 search_doctors CALLED with args: {args}", flush=True)
    # Use the correct API endpoint
    url = "https://wic-doctor.com/api/doctors"
    params = {
        "limit": 10,
        "offset": 0,
    }
    # Map 'search' or 'query' to the 'search' parameter
    search_term = args.get("search") or args.get("query")
    if search_term:
        params["search"] = search_term

    for key in ["specialite", "ville", "gouvernorat", "langue", "type_doctor", "genre"]:
        if key in args and args[key] is not None:
            params[key] = args[key]
    if "en_ligne" in args and args["en_ligne"] is not None:
        params["enLigne"] = str(args["en_ligne"]).lower()

    print(f"🔍 Request URL: {url} with params: {params}", flush=True)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"🔍 Raw response keys: {data.keys()}", flush=True)
                    doctors = data.get("doctors", [])   # ✅ key is "doctors"
                    print(f"🔍 Found {len(doctors)} doctors", flush=True)
                    result_text = ""
                    if not doctors:
                        result_text = "Aucun médecin trouvé avec ces critères."
                    else:
                        for doc in doctors:
                            name = doc.get("name", "Nom inconnu")
                            specialty = doc.get("specialty", "Non spécifiée")
                            location = doc.get("location", "")
                            phone = doc.get("phone", "")
                            aleatoire = doc.get("aleatoire", "")
                            result_text += f"- {name} ({specialty}) - {location} - {phone} [ID: {aleatoire}]\n"
                    return ToolResult(result_text, ToolResultDirection.TO_SERVER)
                else:
                    logger.error(f"Doctor search failed: {resp.status}")
                    return ToolResult("Désolé, je n'ai pas pu accéder à la base des médecins pour le moment.", ToolResultDirection.TO_SERVER)
        except Exception as e:
            logger.error(f"Doctor search exception: {e}")
            return ToolResult("Désolé, une erreur technique s'est produite lors de la recherche.", ToolResultDirection.TO_SERVER)

def doctor_search_tool() -> Tool:
    return Tool(schema=_doctor_search_schema, target=_search_doctors_tool)
