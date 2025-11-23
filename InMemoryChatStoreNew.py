# InMemoryChatStore.py
import json
from typing import Dict, List, Any


class InMemoryChatStoreNew:
	"""
    In-memory chat store that maintains user conversation history.
    Data persists in memory while the application is running.
    """

	SYSTEM_PROMPT = """
You are an AI assistant for Super Clinic.
Your job is to help users book, view, or filter doctor appointments by interacting with the backend via available tools (functions).

Follow these rules:
1. Always use the available functions to retrieve doctor or appointment data — do NOT make assumptions.
2. When booking, ensure to check doctor availability first.
3. when users ask for availability of doctor then always ask for the date and time need to book before retrieving availability.
4. Always confirm success or failure clearly.
5. If no slots are available, use the function to recommend two alternative slots for the same specialty.
6. Respond in a friendly, conversational tone.
7. At the final step of slot booking, validate that the patient's name, email, and phone number are all provided. 
If any of these required fields are missing, the booking must be halted. Instead of proceeding, return a structured error
 response in the following format:

{
  "status": "error",
  "message": "Missing required patient details.",
  "required_fields": ["name", "email", "phone"]
}

Supported user actions:
1. View list of all doctors.
2. Filter doctors by specialty.
3. Show doctor availability.
4. Book appointments based on availability.
5. Recommend alternate slots if unavailable.
6. Also consider user can give the disease detail your responsibility to find the actual doctors list based on which 
specialty it will come if no doctor is available, you can return Sorry, we do not have any doctors with that specialty 
at our Super clinic.




Unsupported queries
- If the user asks anything unrelated to doctor listings, availability, or booking (general clinic operations, billing, prescriptions, medical advice beyond scheduling), respond:
  Sorry, I can only help with doctor appointments. For other queries, please contact our help desk at 12356789.
When booking is successful, respond with:
"Your appointment is confirmed with [Doctor Name] on [Date] at [Time]. Your booking ID is [slotId]."
"""

	FUNCTIONS = [
		{
			"name": "get_doctors",
			"description": "Fetch all doctors from the database.",
			"parameters": {"type": "object", "properties": {}},
		},
		{
			"name": "filter_doctors",
			"description": "Fetch doctors by medical specialty from the database.",
			"parameters": {
				"type": "object",
				"properties": {
					"specialty": {
						"type": "string",
						"description": "The medical specialty, e.g. Cardiologist or Neurologist",
					}
				},
				"required": ["specialty"],
			},
		},
		{
			"name": "get_doctor_availability",
			"description": "Get available appointment slots for a specific doctor on a given date. consider date is optional",
			"parameters": {
				"type": "object",
				"properties": {
					"doctor_name": {"type": "string"},
					"date": {"type": "string", "description": "YYYY-MM-DD"}
				},
				"required": ["doctor_name"]
			}
		},
		{
			"name": "book_appointment",
			"description": "Book a doctor appointment if the selected time slot is available.",
			"parameters": {
				"type": "object",
				"properties": {
					"user_id": {"type": "string", "description": "ID of the user (optional)"},
					"doctor_name": {"type": "string"},
					"date": {"type": "string", "description": "Appointment date (YYYY-MM-DD)"},
					"time": {"type": "string", "description": "Slot time range, e.g. 12:00-13:00"},
					"patient_name": {"type": "string"},
					"email": {"type": "string"},
					"phone": {"type": "string"}
				},
				"required": ["doctor_name", "date", "time", "patient_name", "email", "phone"],
			},
		},
		{
			"name": "recommend_alternatives",
			"description": "Recommend alternate slots for a doctor / specialty.",
			"parameters": {
				"type": "object",
				"properties": {
					"doctor_name": {"type": "string"},
					"date": {"type": "string"},
					"start_time": {"type": "string", "description": "HH:MM:SS"},
					"end_time": {"type": "string", "description": "HH:MM:SS"},
					"specialty": {"type": "string"}
				},
				"required": ["doctor_name", "date", "start_time", "end_time"],
			},
		},
	]

	# Class-level storage: Dict[str, List[Dict[str, Any]]]
	# key: userid (str)
	# value: list of message objects (List[Dict[str, Any]])
	_user_history: Dict[str, List[Dict[str, Any]]] = {}

	@classmethod
	def ensure_user(cls, user_id: str) -> None:
		"""Ensure the user has an entry; if not, initialize with the system prompt."""
		if user_id not in cls._user_history:
			cls._user_history[user_id] = [{"role": "system", "content": cls.SYSTEM_PROMPT}]

	@classmethod
	def add_message(cls, user_id: str, message: Dict[str, Any]) -> None:
		"""
        Add a message to the user's chat history.

        If user_id doesn't exist, initialize with SYSTEM_PROMPT first.
        Args:
            user_id: The unique identifier for the user
            message: A dictionary representing a message (e.g., {"role": "user", "content": "..."})
        """
		cls.ensure_user(user_id)
		cls._user_history[user_id].append(message)

	@classmethod
	def get_messages(cls, user_id: str) -> List[Dict[str, Any]]:
		"""
        Get all messages for a specific user.

        Returns empty list if user doesn't exist.
        """
		return cls._user_history.get(user_id, [])

	@classmethod
	def set_messages(cls, user_id: str, messages: List[Dict[str, Any]]) -> None:
		"""
        Replace the entire message history for a specific user.

        If the provided messages list is empty or None, initialize with the system prompt only.

        Args:
            user_id: The unique identifier for the user
            messages: A list of message dictionaries to store for the user
        """
		if not messages:
			cls._user_history[user_id] = [{"role": "system", "content": cls.SYSTEM_PROMPT}]
		else:
			# Ensure system prompt exists as the first message. If user provided messages
			# that don't start with system prompt, we add it.
			if len(messages) == 0 or messages[0].get("role") != "system":
				messages = [{"role": "system", "content": cls.SYSTEM_PROMPT}] + messages
			cls._user_history[user_id] = messages

	@classmethod
	def clear_user_messages(cls, user_id: str) -> bool:
		"""
        Clear all messages for a particular user.

        Returns True if user existed and was cleared, False otherwise.
        """
		if user_id in cls._user_history:
			del cls._user_history[user_id]
			return True
		return False

	@classmethod
	def get_all_user_ids(cls) -> List[str]:
		"""Get list of all user IDs that have chat history."""
		return list(cls._user_history.keys())

	@classmethod
	def has_user(cls, user_id: str) -> bool:
		"""Check if a user has chat history."""
		return user_id in cls._user_history

	@classmethod
	def get_user_message_count(cls, user_id: str) -> int:
		"""Get the number of messages for a specific user."""
		return len(cls._user_history.get(user_id, []))
	
	@classmethod
	def print_user_history(cls, user_id: str = None) -> None:
		"""
		Print the user history in formatted JSON to the console.
		
		Args:
			user_id: If provided, prints only that user's history. 
			         If None, prints all users' history.
		"""
		print("\n" + "start")
		print("📋 USER HISTORY (JSON Format)")
		print("=" * 80)
		
		if user_id:
			# Print specific user
			if user_id in cls._user_history:
				print(f"\nUser ID: {user_id}")
				print(json.dumps({user_id: cls._user_history[user_id]}, indent=2, ensure_ascii=False))
			else:
				print(f"\n❌ User '{user_id}' not found in history.")
		else:
			# Print all users
			if cls._user_history:
				print(json.dumps(cls._user_history, indent=2, ensure_ascii=False))
			else:
				print("\n📭 No user history found. The store is empty.")
		
		print("End"+ "\n")
	
	@classmethod
	def print_all_history(cls) -> None:
		"""Print all user history in formatted JSON to the console."""
		cls.print_user_history()
