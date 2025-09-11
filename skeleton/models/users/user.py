class User:
    _next_id = 1
    def __init__(self, name: str, phone_number, email: str):
        self.name = name
        self.phone_number = phone_number
        self.email = email

        self._user_id = User._next_id
        User._next_id += 1

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise ValueError("Name must be a string.")
        if len(value) < 3:
            raise ValueError("Name is too short")
        if len(value) > 30:
            raise ValueError("Name is too long")
        self._name = value.strip()

    @property
    def phone_number(self):
        return self._phone_number
    
    @phone_number.setter
    def phone_number(self, value):
        # 04xx xxx xxx
        if not value:
            self._phone_number = "No phone number provided"
        else:
            if not isinstance(value, str) or not value.isdigit():
                raise ValueError("Phone number must contain only digits")
            if len(value.strip()) != 10:
                raise ValueError("Invalid phone number. Phone number must be exactly 10 digits.")
            if not value.strip().startswith("04"):
                raise ValueError("Invalid phone number. Australian phone numbers start with '04'.")
            
            self._phone_number = value.strip()

    @property
    def email(self):
        return self._email
    
    @email.setter
    def email(self, value):
        if not value:
            self._email = "No email provided"
        else: 
            if not isinstance(value, str):
                raise ValueError("Email must be a string.")
            if "@" not in value or "." not in value.split("@")[-1]:
                raise ValueError("Invalid email address format.")
            self._email = value.strip()