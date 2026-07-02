import aiohttp
import asyncio
import json
import logging
from backend.tools.doctor_search import doctor_search_tool
from backend.tools.get_doctor_details import doctor_details_tool

logger = logging.getLogger("voicerag")

class RTMiddleTier:
    def __init__(self, endpoint, deployment, credentials):
        self.endpoint = endpoint
        self.deployment = deployment
        self.credentials = credentials
        self.tools = {}
        self.system_message = ""
        self.search_doctors_tool = doctor_search_tool()
        self.get_doctor_details_tool = doctor_details_tool()

    def set_voice_by_language(self, language):
        pass

    async def forward_messages(self, ws, is_acs_audio_stream):
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                # Intercept user messages
                if data.get("type") == "conversation.item.create":
                    item = data.get("item", {})
                    if item.get("type") == "message" and item.get("role") == "user":
                        for part in item.get("content", []):
                            if part.get("type") == "input_text":
                                user_text = part.get("text", "")
                                # Process the user text to detect intents
                                await self._process_user_text(ws, user_text)
                                continue
                # Forward other messages to the realtime API (if needed)
                # For simplicity, we just handle the user messages ourselves.
            else:
                print(f"Unhandled message type: {msg.type}")

    async def _process_user_text(self, ws, user_text):
        """Detect intent and call appropriate tool."""
        user_lower = user_text.lower()
        # 1. Check if user is asking for doctor details (contains "details", "plus d'infos", etc.)
        if any(kw in user_lower for kw in ["détail", "plus d'info", "en savoir", "details", "infos"]):
            # Try to extract the doctor ID from the conversation context? 
            # For simplicity, we'll ask the user for the ID or name.
            # In this version, we assume the user mentions the doctor name, so we'll search first.
            # Actually, to get details, we need the aleatoire ID. We can search first, then ask.
            # Better to ask the user for the name.
            # But we can also search for the name and then call details on the first result.
            # Let's implement a simple flow: search by name, then auto-detail.
            # For now, we'll just reply asking for the doctor's full name.
            reply = "Pour obtenir plus de détails, veuillez me donner le nom complet du médecin (ex: Dr GHARNATEI Saad)."
            await self._send_text_message(ws, reply)
            return

        # 2. Check if user is asking to find a doctor
        doctor_keywords = ["médecin", "doctor", "cherche", "trouve", "généraliste", "cardiologue", "dentiste", "pédiatre", "ophtalmologue", "dermatologue", "psychiatre"]
        if any(kw in user_lower for kw in doctor_keywords) or "dr" in user_lower:
            # Extract search term (try to get the full name after "Dr" or "docteur")
            import re
            # Look for "Dr [Name]" or "docteur [Name]" or just the name if it looks like a name
            name_match = re.search(r'(?:Dr|docteur|doctor)\s+([A-Za-z\s]+)', user_text, re.I)
            if name_match:
                search_term = name_match.group(1).strip()
            else:
                # If no "Dr", use the whole text as query (but limit to first few words)
                words = user_text.split()
                # If the text has fewer than 5 words, use all; else take first 5
                if len(words) <= 5:
                    search_term = user_text.strip()
                else:
                    search_term = " ".join(words[:5])
            # Call the search tool
            result = await self.search_doctors_tool.target({"search": search_term})
            reply = result.text
            # Send the result
            await self._send_text_message(ws, reply)
            return

        # 3. If no intent matched, just forward the message to the LLM? 
        # But we are not actually forwarding to the LLM because we are handling everything here.
        # We can either echo or ask for clarification.
        await self._send_text_message(ws, "Je suis désolé, je n'ai pas compris. Pouvez-vous reformuler ? Par exemple, 'Je cherche un cardiologue' ou 'Dr GHARNATEI Saad'.")

    async def _send_text_message(self, ws, text):
        """Send a text message back to the client."""
        # Create a conversation item with the assistant's text
        message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": text
                    }
                ]
            }
        }
        await ws.send_json(message)
