import aiohttp
import logging
import json
import re
from typing import Any
from backend.tools.tools import Tool, ToolResult, ToolResultDirection

logger = logging.getLogger("voicerag")

_doctor_details_schema = {
    "type": "function",
    "name": "get_doctor_details",
    "description": "Récupère les informations détaillées d'un médecin à partir de son identifiant aléatoire (aleatoire). Utilisez cette fonction quand l'utilisateur demande plus de détails sur un médecin spécifique, par exemple après une recherche.",
    "parameters": {
        "type": "object",
        "properties": {
            "aleatoire": {
                "type": "string",
                "description": "L'identifiant aléatoire du médecin (par exemple '7364091190'). Cet identifiant est retourné dans les résultats de recherche de médecins."
            }
        },
        "required": ["aleatoire"]
    }
}

def get_french_text(field):
    """Extract French text from JSON field (string or dict)."""
    if isinstance(field, str):
        try:
            parsed = json.loads(field)
            if isinstance(parsed, dict):
                return parsed.get("fr", list(parsed.values())[0] if parsed else "")
            return field
        except:
            return field
    elif isinstance(field, dict):
        return field.get("fr", list(field.values())[0] if field else "")
    return field

async def _get_doctor_details_tool(args: Any) -> ToolResult:
    aleatoire = args.get("aleatoire")
    if not aleatoire:
        return ToolResult("L'identifiant du médecin est manquant. Veuillez préciser le médecin concerné.", ToolResultDirection.TO_SERVER)
    
    url = f"https://backend.wic-doctor.com/getdocbyidblogsnotif/{aleatoire}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    name = get_french_text(data.get("name", "Nom inconnu"))
                    titre = data.get("titre", "")
                    full_name = f"{titre} {name}".strip()
                    
                    # Specialities
                    specialities = data.get("specialities", [])
                    spec_list = []
                    for s in specialities:
                        spec_name = s.get("name", "")
                        spec_str = get_french_text(spec_name)
                        if spec_str:
                            spec_list.append(spec_str)
                    spec_str = ", ".join(spec_list) if spec_list else "Non spécifiée"
                    
                    phone = data.get("phone_number", "Non renseigné")
                    email = data.get("email", "Non renseigné")
                    ville = get_french_text(data.get("ville", "Non renseigné"))
                    gouvernorat = get_french_text(data.get("gouvernorat", "Non renseigné"))
                    adresse = get_french_text(data.get("adresse_exacte", "Non renseignée"))
                    pays = get_french_text(data.get("pays", "Non renseigné"))
                    langues = data.get("langues", "Non renseigné")
                    type_consultation = data.get("type_consultation", "Non renseigné")
                    type_rendezvous = data.get("type_rendezvous", [])
                    type_rendezvous_str = ", ".join(type_rendezvous) if type_rendezvous else "Non renseigné"
                    payment_methodes = data.get("payment_methodes", "Non renseigné")
                    stationnement = data.get("stationnement", "Non renseigné")
                    accessibilite = data.get("accessibilité", "Non renseigné")
                    facebook = data.get("facebook", None)
                    instagram = data.get("instagram", None)
                    siteweb = data.get("siteweb", None)
                    
                    desc = get_french_text(data.get("description", ""))
                    clean_desc = re.sub(r'<[^>]+>', '', desc) if desc else ""
                    
                    tags = data.get("tags", [])
                    tag_list = []
                    for t in tags:
                        tag_name = t.get("name", "")
                        tag_str = get_french_text(tag_name)
                        if tag_str:
                            tag_list.append(tag_str)
                    tag_str = ", ".join(tag_list) if tag_list else "Aucun tag"

                    result_text = f"**{full_name}**\n"
                    result_text += f"Spécialités: {spec_str}\n"
                    result_text += f"Téléphone: {phone}\n"
                    if email and email != "Non renseigné": result_text += f"Email: {email}\n"
                    result_text += f"Ville: {ville}\n"
                    result_text += f"Gouvernorat: {gouvernorat}\n"
                    result_text += f"Adresse: {adresse}\n"
                    if pays and pays != "Non renseigné": result_text += f"Pays: {pays}\n"
                    result_text += f"Langues parlées: {langues}\n"
                    result_text += f"Type de consultation: {type_consultation}\n"
                    result_text += f"Types de rendez-vous: {type_rendezvous_str}\n"
                    result_text += f"Moyens de paiement: {payment_methodes}\n"
                    if stationnement and stationnement != "Non renseigné": result_text += f"Stationnement: {stationnement}\n"
                    if accessibilite and accessibilite != "Non renseigné": result_text += f"Accessibilité: {accessibilite}\n"
                    if facebook: result_text += f"Facebook: {facebook}\n"
                    if instagram: result_text += f"Instagram: {instagram}\n"
                    if siteweb: result_text += f"Site web: {siteweb}\n"
                    if clean_desc:
                        result_text += f"Description: {clean_desc[:500]}{'...' if len(clean_desc)>500 else ''}\n"
                    if tag_str and tag_str != "Aucun tag":
                        result_text += f"Tags: {tag_str}"
                    return ToolResult(result_text, ToolResultDirection.TO_SERVER)
                else:
                    logger.error(f"Doctor details fetch failed: {resp.status}")
                    return ToolResult("Désolé, je n'ai pas pu récupérer les détails de ce médecin pour le moment.", ToolResultDirection.TO_SERVER)
        except Exception as e:
            logger.error(f"Doctor details exception: {e}")
            return ToolResult("Une erreur technique s'est produite lors de la récupération des détails.", ToolResultDirection.TO_SERVER)

def doctor_details_tool() -> Tool:
    return Tool(schema=_doctor_details_schema, target=_get_doctor_details_tool)
