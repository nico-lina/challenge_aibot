from cat.mad_hatter.decorators import tool
from .utils import *
from cat.plugins.super_cat_form.super_cat_form import SuperCatForm, form_tool, super_cat_form
from pydantic import BaseModel, constr, validator, Field, root_validator, field_validator
import re


@tool(
    return_direct = True,
    examples = ["Dammi i dettagli di tutti i dipendenti",
                "Mostrami tutti i dipendenti",
                "Quali sono i dipendenti?",
                "Dimmi i dettagli dei dipendenti",
                ]
)

def get_employees_tool(tool_input, cat):
    """Recupera tutti i dipendenti da Odoo e restituisce una tabella formattata."""
    
    mark = get_employees()

    output = cat.llm(
        f"""Scrivi in modo chiaro per l'utente, applicando una formattazione adeguata i dati contenuti in questa tabella.
        {mark}
        """, stream=True) 
    
    return output.replace("**", "")

def clean_string(s):
    """Rimuove caratteri speciali e converte in minuscolo, mantenendo solo lettere."""
    return re.sub(r"[^a-z]", "", s.lower())

class Employee(BaseModel):
    name: constr(min_length=1)
    job_title: constr(min_length=1)
    work_phone: constr(min_length=1)
    job_id: int
    resource_calendar: int

    @field_validator("work_phone")
    @classmethod
    def validate_work_phone(cls, value):
        """Valida il numero di telefono per accettare solo cifre, spazi, +, -, e parentesi."""
        if not re.match(r"^\+?[0-9\s\-()]+$", value):
            raise ValueError("Invalid phone number format")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        """Valida il nome per assicurarsi che abbia almeno due parole."""
        if len(value.split()) < 2:
            raise ValueError("Name must include both first and last name")
        return value

@super_cat_form
class EmployeeForm(SuperCatForm):
    description = "Crea un nuovo dipendente in Odoo."
    model_class = Employee
    start_examples = ["Crea un nuovo dipendente","Aggiungi un dipendente","Inserisci un nuovo dipendente"]
    stop_examples = ["Non voglio più aggiungere un dipendente","Interrompi la creazione di un dipendente","Esci dalla creazione di un dipendente"]
    ask_confirm = True

    def submit(self, form_data):
        name = form_data["name"]
        job_title = form_data["job_title"]
        work_phone = form_data["work_phone"]
        job_id = form_data["job_id"]
        resource_calendar = form_data["resource_calendar"]
        
        name_parts = name.split()
    
        if len(name_parts) < 2:
            raise ValueError("Il nome deve contenere almeno un nome e un cognome")

        # Pulizia di ogni parte del nome
        first_name = clean_string(name_parts[0])  # Primo nome
        last_names = [clean_string(part) for part in name_parts[1:]]  # Tutti i cognomi puliti

        # Unisce i cognomi con "_" per creare l'email
        last_name = "_".join(last_names)

        work_email = f"{first_name}_{last_name}@azienda.com"

        result = create_employee(name, job_title, work_phone, work_email, job_id, resource_calendar)
        
        print("RESULT", result)

        prompt = f"""Scrivi che il dipendente è stato creato con successo. scrivi i seguenti dettagli in maniera chiara per l'utente:
        {result}
        """
        
        return {"output":f"{self.cat.llm(prompt, stream=True)}"}
    
    def message_wait_confirm(self):
        prompt = (
            "Riassumiamo brevemente i dettagli raccolti:\n"
            f"{self._generate_base_message()}\n"
            "Dopo il riassunto dei dettaglio Scrivi qualcosa come, 'I dati sono corretti? Rispondi dicendo Si puoi inserirlo'"
        )

        print(self._state)
        return {"output": f"{self.cat.llm(prompt)}"}
    
    def message_incomplete(self):
        job_names = get_job_names()
        department_names = get_resource_calendar()
        prompt = (
            f"Nel form mancano alcuni dettagli:\n{self._generate_base_message()}\n"
            f"""In base a ciò che è ancora necessario,
            crea un suggerimento per aiutare l'utente a compilare il
            form di creazione del dipendente.
            Per aiutare l'utente dai queste informazioni sugli id dei job e dei calendari.
            id dei job: {job_names}
            id dei calendari: {department_names}
            """
        )
        return {"output": f"{self.cat.llm(prompt)}"}
    

@tool(
    return_direct = True,
    examples = ["Trovami i nomi dei lavori"],
)

def get_job_names_tool(tool_input, cat):
    """Recupera i nomi dei lavori disponibili in Odoo."""
    job_names = get_job_names()

    output = cat.llm(
        f"""Ecco i nomi dei lavori disponibili:
        {job_names}
        """, stream=True) 
    
    return output.replace("**", "")
