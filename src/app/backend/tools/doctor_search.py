import aiohttp
import logging
from typing import Any
from backend.tools.tools import Tool, ToolResult, ToolResultDirection

logger = logging.getLogger("voicerag")

_doctor_search_schema = {
    "type": "function",
    "name": "search_doctors",
    "description": "Recherche des médecins selon spécialité, ville, gouvernorat, langue, etc. Retourne une liste de médecins avec leurs coordonnées.",
    "parameters": {
        "type": "object",
        "properties": {
            "specialite": {"type": "string", "description": "Spécialité médicale (ex: cardiologue, dentiste)"},
            "ville": {"type": "string", "description": "Ville du médecin"},
            "gouvernorat": {"type": "string", "description": "Gouvernorat (ex: Nabeul, Tunis)"},
            "langue": {"type": "string", "description": "Langue parlée (ex: Français, Anglais)"},
            "query": {"type": "string", "description": "Recherche libre (nom, spécialité, ville)"},
            "type_doctor": {"type": "string", "enum": ["conventionné", "non-conventionné"]},
            "genre": {"type": "string", "enum": ["homme", "femme"]},
            "en_ligne": {"type": "boolean", "description": "Consultation en ligne disponible"}
        },
        "required": []
    }
}

async def _search_doctors_tool(args: Any) -> ToolResult:
    print(f"🔍 search_doctors CALLED with args: {args}", flush=True)
    url = "https://backend.wic-doctor.com/doctorsadd"
    params = {
        "limit": 5,
        "offset": 0,
    }
    for key in ["specialite", "ville", "gouvernorat", "langue", "query", "type_doctor", "genre"]:
        if key in args and args[key] is not None:
            params[key] = args[key]
    if "en_ligne" in args and args["en_ligne"] is not None:
        params["enLigne"] = str(args["en_ligne"]).lower()

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result_text = ""
                    doctors = data.get("data", [])[:5]
                    if not doctors:
                        result_text = "Aucun médecin trouvé avec ces critères."
                    else:
                        for doc in doctors:
                            name = doc.get("name", "Nom inconnu")
                            speciality = doc.get("specialities", "Non spécifiée")
                            city = doc.get("ville_display", "")
                            phone = doc.get("phone_number", "")
                            result_text += f"- {name} ({speciality}) - {city} - {phone}\n"
                    return ToolResult(result_text, ToolResultDirection.TO_SERVER)
                else:
                    logger.error(f"Doctor search failed: {resp.status}")
                    return ToolResult("Désolé, je n'ai pas pu accéder à la base des médecins pour le moment.", ToolResultDirection.TO_SERVER)
        except Exception as e:
            logger.error(f"Doctor search exception: {e}")
            return ToolResult("Désolé, une erreur technique s'est produite lors de la recherche.", ToolResultDirection.TO_SERVER)

def doctor_search_tool() -> Tool:
    return Tool(schema=_doctor_search_schema, target=_search_doctors_tool)
