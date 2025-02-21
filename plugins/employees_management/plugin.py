from cat.mad_hatter.decorators import tool
from .utils import *
from cat.plugins.super_cat_form.super_cat_form import SuperCatForm,  super_cat_form
from pydantic import BaseModel, constr, field_validator
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
    """Recupera tutti i dipendenti da Odoo e restituisce una tabella formattata.
    L'input è sempre None"""
    try:
        mark = get_employees()
        output = cat.llm(
            f"""Scrivi in modo chiaro per l'utente, applicando una formattazione adeguata ai dati contenuti in questa tabella.
            {mark}
            """, stream=True) 
        return output.replace("**", "")
    except Exception as e:
        return cat.llm(f"Scrivi che si è verificato questo errore {str(e)}")

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
    stop_examples = ["Non voglio più aggiungere un dipendente",
                     "Interrompi la creazione di un dipendente",
                     "Esci dalla creazione di un dipendente", 
                     "Non voglio più creare il dipendente"]
    ask_confirm = True

    def submit(self, form_data):
        
        name = form_data["name"]
        name_parts = name.split()
    
        if len(name_parts) < 2:
            raise ValueError("Il nome deve contenere almeno un nome e un cognome")

        # Pulizia di ogni parte del nome
        first_name = clean_string(name_parts[0])  # Primo nome
        last_names = [clean_string(part) for part in name_parts[1:]]  # Tutti i cognomi puliti

        # Unisce i cognomi con "_" per creare l'email
        last_name = "_".join(last_names)

        work_email = f"{first_name}_{last_name}@azienda.com"

        result = create_employee(form_data, work_email)
        

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

    def message_closed(self): 
        prompt = (
            f""" L'utente non vuole più inserire un nuovo dipendente, rispondi che va bene e chiedi se ha bisogno di altro
            """
        )
        return {"output": f"{self.cat.llm(prompt)}"}
    
    
@tool(
    return_direct = True,
    examples = ["Trovami i nomi dei lavori",
                "Quali sono i nomi associati agli id dei lavori?"],
)

def get_job_names_tool(tool_input, cat):
    """Recupera i nomi dei lavori disponibili in Odoo.
    L'input è sempre None"""
    try:
        job_names = get_job_names()
        output = cat.llm(
            f"""Ecco i nomi dei lavori disponibili:
            {job_names}
            """, stream=True) 
        return output.replace("**", "")
    except Exception as e:
        return cat.llm(f"Scrivi che si è verificato questo errore {str(e)}")

@tool(
    return_direct = True,
    examples = ["Completa automaticamente il dipendente X a partire dal suo curriculum",
                "Voglio completare la scheda di X partendo dal suo curriculum",
                "Aggiungi le informazioni personali di X"]
)

def complete_employee_tool(tool_input, cat):
    """Completa la scheda di un dipendente in maniera automatica prendendo le informazioni richieste dal Curriculum
    L'input è sempre il nome del dipendente"""
    try:
        declarative_memory = cat.working_memory.declarative_memories
        curriculum = ""
        for documento in declarative_memory:
            doc = documento[0]
            match = is_cv_matching(doc.metadata["source"], tool_input)
            if match:
                curriculum += doc.page_content

        prompt = f""""{curriculum}
            Dal curriculum passato cerca, se ci sono, queste informazioni e scrivile in formato JSON
            paese di residenza (private country)
            numero di telefono (mobile phone)
            email (private email)
            campo di studi (study field)
            scuola frequentata, in questo caso quella più recente (study school)
            compleanno (birthday)
            Se non è specificato metti come default null
            In output metti solo i campi, senza mettere altro all'interno dell'output SENZA LA SCRITTA json INIZIALE"""
        
        out = cat.llm(prompt, stream = True)
        result = complete_secondary_info(tool_input, out)
        out = cat.llm(f"""Scrivi che sono state aggiornate le informazioni recuperando i dati dal curriculum. 
                      Scrivi i seguenti dettagli in maniera chiara per l'utente:
                    {result}
                    Scrivi inoltre che se l'utente vuole aggiungere altre informazioni non specificate nel curriculum di visitare il link scritto nel risultato.
                    """)
        return out.replace("**", "")
    except Exception as e:
        return cat.llm(f"Scrivi che si è verificato questo errore {str(e)}")

@tool(
    return_direct = True,
    examples = ["Inserisci le informazioni relative agli studi e alla carriera del dipendente X",
                "Aggiorna le informazioni relative agli studi e alla carriera di X",
                "Aggiorna il curriculum di X"]
)

def complete_curriculum_tool(tool_input, cat):
    """Completa la parte relativa alle esperienze lavorative e di studi del dipendente prendendole dal curriculum
    L'input è sempre il nome del dipendente"""
    try:
        declarative_memory = cat.working_memory.declarative_memories
        curriculum = ""
        for documento in declarative_memory:
            doc = documento[0]
            print("DOC.CONTENT", doc.page_content)
            match = is_cv_matching(doc.metadata["source"], tool_input)
            if match:
                curriculum += doc.page_content

        prompt = f""""{curriculum}
            Dal curriculum passato cerca, se ci sono, queste informazioni e scrivile in formato JSON
            Trovi diverse informazioni crea diversi JSON
            nome, è il nome della scuola, del posto di lavoro, o del progetto (name)
            descrizione, è la descrizione BREVE (massimo 10 parole) del ruolo a lavoro, del progetto, o del percorso di studi (description)
            data di inizio, è la data di fine del lavoro, del progetto o di quando ha iniziato a frequentare il percorso di studi (date_start)
            data di fine, è la data di inizio del lavoro, del progetto o di quando ha finito di frequentare il percorso di studi (date_end)
            Se non è specificato metti come default null
            Se nelle date è specificato solo l'anno scrivi YYYY-01-01 per le date di inizio e YYYY-12-31 per le date di fine
            In output metti solo i campi, senza mettere altro all'interno dell'output SENZA LA SCRITTA json INIZIALE
            Infine aggiungi anche un campo che si chiama line_type_id che è:
            2 -> Se si sta parlando di percorso di Istruzione (scuola, università, corsi ecc...)
            1 -> Se si sta parlando di Esperienze di Lavoro o di volontariato
            4 -> Se si sta parlando di progetti che non rientrano nel mondo del lavoro"""
        
        result = cat.llm(prompt)
        info = complete_curriculum_info(tool_input, result)

        out = cat.llm(f"""Scrivi che sono state aggiornate le informazioni recuperando i dati dal curriculum. 
                      Scrivi i seguenti dettagli in maniera chiara per l'utente:
                    {info}
                    Scrivi inoltre che se l'utente vuole aggiungere altre informazioni non specificate nel curriculum di visitare il link scritto nel risultato.
                    """)
        return out.replace("**", "")
    except Exception as e:
        return cat.llm(f"Scrivi che si è verificato questo errore {str(e)}")
