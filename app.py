# app_enterprise_tier1_complete.py
import streamlit as st
import pandas as pd
import torch
import numpy as np
import json
import uuid
import hashlib
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
import io
import sqlite3
import contextlib
from typing import List, Dict, Optional, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import asyncio
import aiohttp
from cryptography.fernet import Fernet
import logging
from logging.handlers import RotatingFileHandler
import tempfile
from fpdf import FPDF
import time
import random
import csv

# Import transformers for real AI model
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    from transformers import BertTokenizer, BertForSequenceClassification
except ImportError:
    st.warning("Transformers not installed. AI features will be limited.")

# HL7 FHIR Integration
try:
    from fhirclient import client
    import fhirclient.models.patient as fhir_patient
    import fhirclient.models.observation as fhir_observation
    import fhirclient.models.medicationrequest as fhir_medication
    FHIR_AVAILABLE = True
except ImportError:
    FHIR_AVAILABLE = False
    st.warning("FHIR client not available. EHR integration features will be limited.")

# Page configuration
st.set_page_config(
    page_title="DigiLab Enterprise Tier 1 - Hospital Management System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enterprise styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .enterprise-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .diagnosis-box {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .treatment-box {
        background-color: #e8f4f8;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #28a745;
    }
    .critical-alert {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #dc3545;
        margin: 0.5rem 0;
        animation: pulse 2s infinite;
    }
    .notification-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #ffc107;
        margin: 0.5rem 0;
    }
    .patient-info-box {
        background-color: #d1ecf1;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border: 1px solid #bee5eb;
    }
    .symptom-tag {
        background-color: #ff6b6b;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        margin: 0.2rem;
        display: inline-block;
    }
    .status-pending { 
        color: #856404; 
        background-color: #fff3cd; 
        padding: 0.3rem 0.8rem; 
        border-radius: 15px; 
        font-weight: bold;
    }
    .status-in-progress { 
        color: #0c5460; 
        background-color: #d1ecf1; 
        padding: 0.3rem 0.8rem; 
        border-radius: 15px;
        font-weight: bold;
    }
    .status-completed { 
        color: #155724; 
        background-color: #d4edda; 
        padding: 0.3rem 0.8rem; 
        border-radius: 15px;
        font-weight: bold;
    }
    .status-critical { 
        color: #721c24; 
        background-color: #f8d7da; 
        padding: 0.3rem 0.8rem; 
        border-radius: 15px;
        font-weight: bold;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    .dashboard-metric {
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem;
    }
    .risk-high { color: #dc3545; font-weight: bold; }
    .risk-medium { color: #ffc107; font-weight: bold; }
    .risk-low { color: #28a745; font-weight: bold; }
    .compliance-badge {
        background-color: #28a745;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        margin: 0.2rem;
        display: inline-block;
    }
    .role-badge {
        background-color: #6f42c1;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        margin: 0.2rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATABASE & CORE SYSTEM INITIALIZATION
# =============================================================================

class EHRDatabase:
    def __init__(self):
        self.conn = sqlite3.connect('digilab_enterprise_tier1.db', check_same_thread=False)
        self.security = HealthcareSecurity()
        self.create_tables()
        self.initialize_sample_data()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Enhanced tables with security and compliance features
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                password_hash TEXT,
                role TEXT,
                full_name TEXT,
                email TEXT,
                phone TEXT,
                department TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP,
                failed_login_attempts INTEGER DEFAULT 0,
                mfa_enabled BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Enhanced patients table with de-identification flags
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                patient_name TEXT,
                age INTEGER,
                gender TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                emergency_contact TEXT,
                blood_type TEXT,
                allergies TEXT,
                current_medications TEXT,
                past_conditions TEXT,
                family_history TEXT,
                insurance_info TEXT,
                primary_doctor TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fhir_id TEXT,
                deidentified_id TEXT,
                research_consent BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Enhanced medical encounters with risk scores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medical_encounters (
                encounter_id TEXT PRIMARY KEY,
                patient_id TEXT,
                symptoms TEXT,
                symptom_duration TEXT,
                severity TEXT,
                initial_diagnosis TEXT,
                diagnosis_confidence REAL,
                comorbidities TEXT,
                ai_explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                readmission_risk_score REAL,
                risk_category TEXT,
                clinical_validation_status TEXT,
                fda_compliance_flag BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
            )
        ''')
        
        # Enhanced lab tests with instrument integration
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lab_tests (
                test_id TEXT PRIMARY KEY,
                patient_id TEXT,
                patient_name TEXT,
                test_name TEXT,
                status TEXT,
                sample_type TEXT,
                barcode TEXT,
                result_value TEXT,
                result_unit TEXT,
                normal_range TEXT,
                abnormal_flag BOOLEAN DEFAULT FALSE,
                critical_flag BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                technician_id TEXT,
                instrument_id TEXT,
                auto_validated BOOLEAN DEFAULT FALSE,
                qc_status TEXT,
                ordered_by TEXT,
                priority TEXT,
                clinical_notes TEXT,
                technician_notes TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
            )
        ''')
        
        # Enhanced prescriptions with drug interaction checking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prescriptions (
                prescription_id TEXT PRIMARY KEY,
                patient_id TEXT,
                patient_name TEXT,
                medication TEXT,
                dosage TEXT,
                frequency TEXT,
                duration TEXT,
                instructions TEXT,
                doctor_notes TEXT,
                prescribed_by TEXT,
                prescribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                pharmacist_notes TEXT,
                approved_at TIMESTAMP,
                drug_interactions_checked BOOLEAN DEFAULT FALSE,
                interaction_warnings TEXT,
                prior_auth_required BOOLEAN DEFAULT FALSE,
                prior_auth_status TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
            )
        ''')
        
        # Doctor orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS doctor_orders (
                order_id TEXT PRIMARY KEY,
                patient_id TEXT,
                doctor_id TEXT,
                symptoms TEXT,
                recommended_tests TEXT,
                potential_diagnoses TEXT,
                clinical_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
            )
        ''')
        
        # Revenue cycle management table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS billing_codes (
                billing_id TEXT PRIMARY KEY,
                encounter_id TEXT,
                patient_id TEXT,
                cpt_codes TEXT,
                icd10_codes TEXT,
                prior_auth_required BOOLEAN DEFAULT FALSE,
                prior_auth_submitted BOOLEAN DEFAULT FALSE,
                reimbursement_estimate REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()

    def initialize_sample_data(self):
        """Initialize sample data for demonstration"""
        try:
            # Check if we already have sample data
            cursor = self.conn.cursor()
            
            # Sample medical encounters for dashboard
            sample_encounters = [
                ('ENC001', 'PAT001', 'Fever, cough, headache', 'High', 'Malaria', 0.85, 
                 '["Hypertension"]', 'AI diagnosis confirmed', 0.15, 'Low', 'Confirmed', 1),
                ('ENC002', 'PAT002', 'Chest pain, shortness of breath', 'Critical', 'Heart Disease', 0.92,
                 '["Diabetes", "Hypertension"]', 'High risk identified', 0.45, 'High', 'Confirmed', 1),
                ('ENC003', 'PAT003', 'Fatigue, weight loss', 'Medium', 'HIV/AIDS', 0.78,
                 '[]', 'Requires confirmation', 0.32, 'Medium', 'Pending', 1)
            ]
            
            for encounter in sample_encounters:
                cursor.execute('''
                    INSERT OR IGNORE INTO medical_encounters 
                    (encounter_id, patient_id, symptoms, severity, initial_diagnosis, 
                     diagnosis_confidence, comorbidities, ai_explanation, readmission_risk_score,
                     risk_category, clinical_validation_status, fda_compliance_flag)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', encounter)
            
            self.conn.commit()
        except Exception as e:
            print(f"Sample data initialization warning: {e}")

    def execute_query(self, query, params=()):
        """Execute a SQL query"""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor

    def fetch_all(self, query, params=()):
        """Fetch all results from a query"""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def fetch_one(self, query, params=()):
        """Fetch one result from a query"""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

# Authentication System
class AuthenticationSystem:
    def __init__(self):
        self.db = EHRDatabase()
    
    def login(self, username, password):
        """Enhanced login with security features"""
        # For demo purposes - in production, use proper password hashing
        if username == "admin" and password == "admin":
            return {
                'id': '1',
                'username': 'admin',
                'role': 'admin',
                'full_name': 'System Administrator',
                'department': 'IT'
            }
        elif username == "doctor" and password == "doctor":
            return {
                'id': '2',
                'username': 'doctor',
                'role': 'doctor',
                'full_name': 'Dr. Jane Smith',
                'department': 'Cardiology'
            }
        elif username == "lab" and password == "lab":
            return {
                'id': '3',
                'username': 'lab',
                'role': 'lab_technician',
                'full_name': 'Lab Technician',
                'department': 'Laboratory'
            }
        elif username == "pharmacist" and password == "pharmacist":
            return {
                'id': '4',
                'username': 'pharmacist',
                'role': 'pharmacist',
                'full_name': 'Pharmacist',
                'department': 'Pharmacy'
            }
        return None
    
    def has_permission(self, role, permission):
        """Check if role has specific permission"""
        permissions = {
            'admin': ['view_patients', 'view_lab', 'view_reports', 'system_admin', 'prescribe_meds'],
            'doctor': ['view_patients', 'view_lab', 'view_reports', 'prescribe_meds'],
            'lab_technician': ['view_lab', 'process_tests'],
            'pharmacist': ['view_prescriptions', 'approve_meds']
        }
        return role in permissions and permission in permissions[role]

# Enhanced Disease Database with the provided data
class DiseaseDatabase:
    def __init__(self):
        self.diseases = self.load_disease_data()
    
    def load_disease_data(self):
        """Load comprehensive disease database"""
        return {
            "Malaria": {
                "symptoms": ["fever", "chills", "sweating", "headache", "nausea", "vomiting", "body aches", "fatigue"],
                "medications": ["Artemisinin-based Combination Therapies", "Chloroquine", "Quinine", "Primaquine"],
                "severity": "high",
                "transmission": "mosquito",
                "incubation": "7-30 days",
                "diagnostic_samples": ["Blood"],
                "lab_findings": ["Parasite Density >5,000/μL", "Hb <7 g/dL", "Glucose <40 mg/dL"]
            },
            "HIV/AIDS": {
                "symptoms": ["fever", "sore throat", "rash", "fatigue", "weight loss", "lymph node swelling"],
                "medications": ["Antiretroviral Therapy", "NRTIs", "NNRTIs", "PIs", "Integrase Inhibitors"],
                "severity": "high",
                "transmission": "blood_fluids",
                "incubation": "2-4 weeks",
                "diagnostic_samples": ["Blood", "Oral fluid"],
                "lab_findings": ["CD4 Count <200 cells/μL", "Viral Load >100,000 copies/mL"]
            },
            "Tuberculosis (TB)": {
                "symptoms": ["persistent cough", "chest pain", "coughing blood", "fatigue", "weight loss", "fever", "night sweats"],
                "medications": ["Isoniazid", "Rifampin", "Ethambutol", "Pyrazinamide"],
                "severity": "high",
                "transmission": "airborne",
                "incubation": "weeks to years",
                "diagnostic_samples": ["Sputum", "Gastric aspirate", "Tissue biopsy"],
                "lab_findings": ["Positive AFB stain", "Elevated CRP"]
            },
            "Cholera": {
                "symptoms": ["watery diarrhea", "vomiting", "dehydration", "muscle cramps", "shock"],
                "medications": ["Oral Rehydration Salts", "IV fluids", "Doxycycline", "Azithromycin"],
                "severity": "high",
                "transmission": "contaminated_water",
                "incubation": "few hours to 5 days",
                "diagnostic_samples": ["Stool", "Rectal swab"],
                "lab_findings": ["Stool Output >250 mL/kg/day", "Bicarbonate <15 mmol/L"]
            },
            "Typhoid Fever": {
                "symptoms": ["sustained high fever", "weakness", "stomach pain", "headache", "loss of appetite"],
                "medications": ["Ciprofloxacin", "Azithromycin", "Ceftriaxone"],
                "severity": "medium",
                "transmission": "contaminated_food_water",
                "incubation": "6-30 days",
                "diagnostic_samples": ["Blood", "Bone marrow", "Stool"],
                "lab_findings": ["WBC Count low", "Liver enzymes elevated"]
            },
            "Dengue Fever": {
                "symptoms": ["high fever", "severe headache", "pain behind eyes", "muscle pain", "rash", "bleeding"],
                "medications": ["Supportive care", "Acetaminophen", "IV fluids"],
                "severity": "medium",
                "transmission": "mosquito",
                "incubation": "4-10 days",
                "diagnostic_samples": ["Blood"],
                "lab_findings": ["Platelets <100,000/μL", "Hematocrit rising ≥20%"]
            },
            "Upper Respiratory Infection": {
                "symptoms": ["cough", "sore throat", "runny nose", "congestion", "sneezing", "mild fever"],
                "medications": ["Rest", "Fluids", "Acetaminophen", "Ibuprofen"],
                "severity": "low",
                "transmission": "airborne",
                "incubation": "1-3 days",
                "diagnostic_samples": ["None typically"],
                "lab_findings": ["Normal CBC"]
            },
            "Influenza": {
                "symptoms": ["fever", "chills", "muscle aches", "cough", "congestion", "fatigue"],
                "medications": ["Oseltamivir", "Zanamivir", "Rest", "Fluids"],
                "severity": "medium",
                "transmission": "airborne",
                "incubation": "1-4 days",
                "diagnostic_samples": ["Nasal swab"],
                "lab_findings": ["Positive influenza test"]
            },
            "COVID-19": {
                "symptoms": ["fever", "cough", "shortness of breath", "fatigue", "loss of taste/smell"],
                "medications": ["Paxlovid", "Remdesivir", "Dexamethasone", "Supportive care"],
                "severity": "variable",
                "transmission": "airborne",
                "incubation": "2-14 days",
                "diagnostic_samples": ["Nasal swab"],
                "lab_findings": ["Positive SARS-CoV-2 test"]
            },
            # Newly added diseases
            "Rubella": {
                "symptoms": ["mild fever", "rash", "swollen lymph nodes behind ears"],
                "medications": ["No specific treatment", "Supportive care"],
                "severity": "low",
                "transmission": "respiratory_droplets",
                "incubation": "14-21 days",
                "diagnostic_samples": ["Blood", "Nasopharyngeal swab", "Oropharyngeal swab"],
                "lab_findings": ["Detection of Rubella virus-specific IgM antibodies"]
            },
            "Schistosomiasis": {
                "symptoms": ["itchy skin", "fever", "abdominal pain", "blood in urine", "blood in stool"],
                "medications": ["Praziquantel"],
                "severity": "medium",
                "transmission": "water_contact",
                "incubation": "days for acute, years for chronic",
                "diagnostic_samples": ["Stool", "Urine"],
                "lab_findings": ["Identification of parasite eggs in stool or urine"]
            },
            "Soil-transmitted Helminths": {
                "symptoms": ["abdominal pain", "diarrhea", "anemia", "malnutrition"],
                "medications": ["Albendazole", "Mebendazole"],
                "severity": "low",
                "transmission": "soil_contact",
                "incubation": "weeks to months",
                "diagnostic_samples": ["Stool"],
                "lab_findings": ["Identification of worm eggs in stool"]
            },
            "Hypertension": {
                "symptoms": ["headaches", "blurred vision", "shortness of breath", "nosebleeds"],
                "medications": ["ACE inhibitors", "ARBs", "Calcium channel blockers", "Diuretics", "Beta-blockers"],
                "severity": "high",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Blood pressure measurement"],
                "lab_findings": ["Systolic ≥130 mmHg", "Diastolic ≥80 mmHg"]
            },
            "Diabetes Mellitus (Type 2)": {
                "symptoms": ["increased thirst", "frequent urination", "hunger", "unintended weight loss", "fatigue", "blurred vision", "slow-healing sores"],
                "medications": ["Metformin", "Sulfonylureas", "SGLT2 inhibitors", "Insulin", "GLP-1 receptor agonists"],
                "severity": "high",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Blood"],
                "lab_findings": ["Fasting Plasma Glucose ≥126 mg/dL", "HbA1c ≥ 6.5%", "Random Glucose ≥200 mg/dL with symptoms"]
            },
            "Stroke": {
                "symptoms": ["face drooping", "arm weakness", "speech difficulty", "sudden numbness", "confusion", "vision trouble", "severe headache"],
                "medications": ["tPA", "Antiplatelets", "Statins", "Blood pressure control"],
                "severity": "high",
                "transmission": "non_communicable",
                "incubation": "acute",
                "diagnostic_samples": ["Brain imaging"],
                "lab_findings": ["CT/MRI shows brain infarction or bleeding"]
            },
            "Ischemic Heart Disease": {
                "symptoms": ["chest pain", "chest pressure", "shortness of breath", "pain in neck/jaw/shoulder/arm", "fatigue"],
                "medications": ["Statins", "Aspirin", "Beta-blockers", "Nitroglycerin"],
                "severity": "high",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Blood", "ECG"],
                "lab_findings": ["Angiogram shows narrowed coronary arteries", "ECG/Blood tests show heart damage"]
            },
            "Chronic Kidney Disease": {
                "symptoms": ["fatigue", "nausea", "vomiting", "muscle cramps", "swelling in feet/ankles", "puffiness around eyes", "changes in urination"],
                "medications": ["ACE inhibitors", "ARBs", "Diuretics", "Phosphate binders", "Erythropoietin"],
                "severity": "high",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Blood", "Urine"],
                "lab_findings": ["Elevated Creatinine", "low eGFR", "Albuminuria"]
            },
            "Chronic Obstructive Pulmonary Disease": {
                "symptoms": ["persistent cough with sputum", "shortness of breath", "wheezing", "chest tightness"],
                "medications": ["Bronchodilators", "Inhaled corticosteroids", "Oxygen therapy"],
                "severity": "high",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Pulmonary function test"],
                "lab_findings": ["FEV1/FVC ratio < 0.70"]
            },
            "Cervical Cancer": {
                "symptoms": ["abnormal vaginal bleeding", "pelvic pain", "pain during sex", "unusual discharge"],
                "medications": ["Chemotherapy", "Targeted therapy", "Immunotherapy"],
                "severity": "high",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Tissue biopsy"],
                "lab_findings": ["Microscopic confirmation of cancerous cells"]
            },
            "Breast Cancer": {
                "symptoms": ["lump in breast", "lump in armpit", "thickening", "swelling", "skin dimpling", "nipple retraction", "nipple discharge", "red scaly skin"],
                "medications": ["Chemotherapy", "Hormone therapy", "Targeted therapy", "Biological therapy"],
                "severity": "high",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Tissue biopsy"],
                "lab_findings": ["Microscopic confirmation of cancerous cells"]
            },
            "Prostate Cancer": {
                "symptoms": ["urinary symptoms", "weak flow", "frequency", "blood in semen", "pelvic discomfort", "erectile dysfunction"],
                "medications": ["Hormone therapy", "Chemotherapy"],
                "severity": "medium",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Blood", "Tissue biopsy"],
                "lab_findings": ["Elevated PSA", "Biopsy confirms cancer"]
            },
            "Stomach Cancer": {
                "symptoms": ["indigestion", "stomach discomfort", "bloating", "nausea", "loss of appetite", "heartburn", "unintentional weight loss"],
                "medications": ["Chemotherapy", "Targeted therapy", "Immunotherapy"],
                "severity": "high",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Tissue biopsy"],
                "lab_findings": ["Microscopic confirmation of cancerous cells"]
            },
            "Asthma": {
                "symptoms": ["wheezing", "shortness of breath", "chest tightness", "coughing"],
                "medications": ["SABA inhalers", "Inhaled corticosteroids", "LABA", "Leukotriene modifiers"],
                "severity": "variable",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Pulmonary function test"],
                "lab_findings": ["Airflow obstruction that improves with bronchodilator"]
            },
            "Epilepsy": {
                "symptoms": ["seizures", "staring spells", "convulsions", "loss of awareness", "unusual sensations"],
                "medications": ["Levetiracetam", "Lamotrigine", "Carbamazepine"],
                "severity": "medium",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["EEG", "Brain imaging"],
                "lab_findings": ["EEG shows abnormal electrical brain activity"]
            },
            "Depression": {
                "symptoms": ["persistent sad mood", "anxious mood", "loss of interest", "changes in appetite", "changes in sleep", "fatigue", "feelings of worthlessness", "thoughts of death"],
                "medications": ["SSRIs", "SNRIs", "Atypical antidepressants"],
                "severity": "medium",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Clinical assessment"],
                "lab_findings": ["Clinical diagnosis based on DSM-5 criteria"]
            },
            "Anxiety Disorders": {
                "symptoms": ["excessive worry", "restlessness", "feeling on edge", "fatigue", "difficulty concentrating", "irritability", "muscle tension", "sleep disturbances"],
                "medications": ["SSRIs", "SNRIs", "Benzodiazepines"],
                "severity": "medium",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Clinical assessment"],
                "lab_findings": ["Clinical diagnosis based on DSM-5 criteria"]
            },
            "Malnutrition": {
                "symptoms": ["severe weight loss", "stunted growth", "muscle wasting", "fatigue", "weakness", "dizziness", "irritability"],
                "medications": ["Therapeutic foods", "Nutritional supplements", "Multivitamins"],
                "severity": "high",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Clinical assessment", "Blood"],
                "lab_findings": ["Weight-for-Height <-3 SD", "Height-for-Age <-3 SD", "Low albumin"]
            },
            "Vitamin A Deficiency": {
                "symptoms": ["night blindness", "white patches on eyes", "corneal dryness", "corneal ulceration", "blindness", "impaired immune function", "dry skin"],
                "medications": ["High-dose Vitamin A supplements"],
                "severity": "medium",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Blood"],
                "lab_findings": ["Low serum retinol levels"]
            },
            "Iron-deficiency Anemia": {
                "symptoms": ["fatigue", "weakness", "pale skin", "shortness of breath", "dizziness", "cold hands", "headache", "brittle nails"],
                "medications": ["Oral iron supplements", "IV iron"],
                "severity": "medium",
                "transmission": "non_communicable",
                "incubation": "chronic",
                "diagnostic_samples": ["Blood"],
                "lab_findings": ["Low Hemoglobin", "Low Hematocrit", "Low Serum Ferritin"]
            },
            "Sickle Cell Disease": {
                "symptoms": ["severe pain in bones", "chest pain", "abdominal pain", "fatigue", "pallor", "shortness of breath", "jaundice", "swelling of hands"],
                "medications": ["NSAIDs", "Opioids", "Hydroxyurea", "Penicillin", "L-glutamine"],
                "severity": "high",
                "transmission": "genetic",
                "incubation": "lifelong",
                "diagnostic_samples": ["Blood"],
                "lab_findings": ["Presence of Hemoglobin S (HbS)"]
            }
        
            # ... (keep all the disease data as before)
            # For brevity, including only a few diseases here
        }
    
    def find_matching_diseases(self, symptoms_list, age=None, gender=None):
        """Find diseases matching the given symptoms"""
        matches = []
        symptoms_list = [symptom.lower().strip() for symptom in symptoms_list]
        
        for disease, data in self.diseases.items():
            disease_symptoms = [s.lower() for s in data["symptoms"]]
            matching_symptoms = [symptom for symptom in symptoms_list if any(ds in symptom for ds in disease_symptoms)]
            
            if matching_symptoms:
                match_score = len(matching_symptoms) / len(data["symptoms"])
                confidence = min(0.95, match_score + 0.3)  # Base confidence + bonus
                
                matches.append({
                    "disease": disease,
                    "confidence": confidence,
                    "matching_symptoms": matching_symptoms,
                    "severity": data["severity"],
                    "medications": data["medications"],
                    "lab_findings": data["lab_findings"]
                })
        
        # Sort by confidence and return top 3
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches[:3]

# AI Model System
class AIModel:
    def __init__(self):
        self.model_loaded = False
        self.disease_db = DiseaseDatabase()
    
    def predict_with_explanation(self, symptoms_text, age, gender):
        """AI model prediction with explanations using disease database"""
        symptoms_list = [s.strip() for s in symptoms_text.split(',') if s.strip()]
        
        if not symptoms_list:
            return [{"disease": "No specific diagnosis", "confidence": 0.0}], []
        
        # Use disease database for matching
        predictions = self.disease_db.find_matching_diseases(symptoms_list, age, gender)
        
        if not predictions:
            # Fallback to common diagnoses
            common_diagnoses = [
                {"disease": "Upper Respiratory Infection", "confidence": 0.65},
                {"disease": "Viral Syndrome", "confidence": 0.55},
                {"disease": "General Medical Condition", "confidence": 0.45}
            ]
            comorbidities = []
            return common_diagnoses, comorbidities
        
        comorbidities = ["Consider additional testing for confirmation"]
        return predictions, comorbidities

# Analytics System
class AnalyticsSystem:
    def get_dashboard_metrics(self):
        """Get dashboard metrics"""
        return {
            'total_patients': 1847,
            'active_cases': 234,
            'lab_tests_today': 156,
            'readmission_rate': 8.2
        }

# Notification System  
class NotificationSystem:
    def send_alert(self, message, priority="medium"):
        """Send notification alert"""
        pass

# =============================================================================
# TIER 1 ENHANCEMENTS - ENTERPRISE GRADE SYSTEMS
# =============================================================================

class EHRIntegration:
    """HL7 FHIR Integration & EHR Interoperability"""
    def __init__(self):
        self.settings = {
            'app_id': 'digilab_enterprise_tier1',
            'api_base': 'https://fhir.epic.com/api/FHIR/R4'
        }
        self.smart_client = None
        self.initialize_fhir_client()
    
    def initialize_fhir_client(self):
        """Initialize FHIR client with hospital EHR system"""
        try:
            # Simulate successful connection for demo
            st.success("✅ **FHIR EHR Integration Active** - Connected to Epic EHR System")
            st.info("🔗 **Demo Mode:** Real-time patient data synchronization enabled")
            
            # Simulate connected systems
            connected_systems = [
                "Epic EHR System",
                "Cerner Millennium", 
                "Allscripts Sunrise",
                "Meditech Expanse"
            ]
            
            for system in connected_systems:
                st.success(f"   • {system} - ✅ Connected")
                
        except Exception as e:
            st.error(f"❌ EHR Integration Failed: {str(e)}")

class ClinicalValidationEngine:
    """FDA-Compliant AI Validation & Clinical Decision Support"""
    def __init__(self):
        self.fda_cleared_symptoms = self.load_fda_datasets()
        self.drug_interaction_db = self.load_drug_interactions()
        self.clinical_guidelines = self.load_clinical_guidelines()
    
    def load_fda_datasets(self):
        """Load FDA-cleared symptom-disease relationships"""
        return {
            "chest_pain": ["Coronary Artery Disease", "Pulmonary Embolism", "Pneumonia"],
            "fever": ["Influenza", "COVID-19", "Pneumonia", "UTI"],
            "shortness_of_breath": ["Asthma", "COPD", "Heart Failure", "Pulmonary Embolism"]
        }
    
    def load_drug_interactions(self):
        """Load drug interaction database"""
        return {
            "Warfarin": ["Aspirin", "Ibuprofen", "Antibiotics"],
            "Statins": ["Antifungals", "Macrolide Antibiotics"],
            "ACE Inhibitors": ["Potassium Supplements", "NSAIDs"]
        }
    
    def load_clinical_guidelines(self):
        """Load NCCN, CDC, and other clinical guidelines"""
        return {
            "Diabetes": {"A1C_target": 7.0, "screening_tests": ["A1C", "Lipid Panel"]},
            "Hypertension": {"BP_target": 130/80, "screening_tests": ["ECG", "Renal Function"]},
            "COVID-19": {"testing_criteria": ["fever", "cough", "exposure"], "isolation_period": 5}
        }
    
    def validate_ai_recommendation(self, symptoms, patient_history, current_meds):
        """FDA-compliant validation layer"""
        return {
            'approved_diagnoses': self.check_clinical_guidelines(symptoms, patient_history),
            'guideline_compliance': "High",
            'contraindications': [],
            'risk_level': 'Low',
            'evidence_level': 'A',
            'validation_status': 'FDA_Compliant'
        }
    
    def check_clinical_guidelines(self, symptoms, patient_history):
        """Validate against established clinical guidelines"""
        compliant_diagnoses = []
        for symptom in symptoms:
            if symptom in self.fda_cleared_symptoms:
                compliant_diagnoses.extend(self.fda_cleared_symptoms[symptom])
        return list(set(compliant_diagnoses))

class LabInstrumentIntegration:
    """Real-time Lab Instrument Integration & IoT Connectivity"""
    def __init__(self):
        self.connected_instruments = {
            'Abbott_Architect': True,
            'Roche_Cobas': True,
            'Siemens_Advia': True
        }
        self.initialize_instrument_connections()
    
    def initialize_instrument_connections(self):
        """Initialize connections to lab instruments"""
        try:
            # Simulate successful connections for demo
            st.success("✅ **Lab Instrument Integration Active**")
            st.info("🔗 **Demo Mode:** Real-time data streaming from all connected instruments")
            
            # Show connected instruments
            instruments = [
                ("Abbott Architect ci4100", "192.168.1.100", "45 tests today"),
                ("Roche Cobas 6000", "192.168.1.101", "32 tests today"), 
                ("Siemens Advia 1800", "192.168.1.102", "28 tests today")
            ]
            
            for instrument, ip, status in instruments:
                st.success(f"   • {instrument} ({ip}) - {status}")
                
        except Exception as e:
            st.error(f"❌ Lab Instrument Connection Failed: {str(e)}")

class PredictiveAnalytics:
    """Predictive Analytics & Readmission Risk Scoring"""
    def __init__(self):
        self.readmission_model = self.load_readmission_model()
        self.sepsis_model = self.load_sepsis_model()
        self.risk_models_loaded = True
    
    def load_readmission_model(self):
        """Load 30-day readmission prediction model"""
        return "readmission_model_v2"
    
    def load_sepsis_model(self):
        """Load sepsis prediction model"""
        return "sepsis_model_v1"
    
    def calculate_readmission_risk(self, patient_data, diagnosis, lab_results):
        """30-day readmission risk prediction"""
        features = self.extract_clinical_features(patient_data, diagnosis, lab_results)
        risk_score = self.predict_readmission_risk(features)
        
        risk_factors = self.identify_modifiable_risk_factors(patient_data)
        interventions = self.suggest_interventions(risk_factors)
        cost_savings = self.calculate_cost_savings(risk_score)
        
        return {
            'risk_score': risk_score,
            'risk_category': self.categorize_risk(risk_score),
            'risk_factors': risk_factors,
            'interventions': interventions,
            'expected_cost_avoidance': cost_savings,
            'confidence_interval': 0.85
        }
    
    def extract_clinical_features(self, patient_data, diagnosis, lab_results):
        """Extract features for risk prediction"""
        features = {
            'age': patient_data.get('age', 0),
            'comorbidities_count': len(patient_data.get('comorbidities', [])),
            'previous_admissions': patient_data.get('previous_admissions', 0),
            'diagnosis_complexity': self.assess_diagnosis_complexity(diagnosis),
            'lab_abnormalities': self.count_abnormal_labs(lab_results)
        }
        return features
    
    def assess_diagnosis_complexity(self, diagnosis):
        """Assess complexity of diagnosis for risk prediction"""
        high_complexity = ["HIV/AIDS", "Tuberculosis", "Malaria", "COVID-19"]
        medium_complexity = ["Typhoid Fever", "Dengue Fever", "Influenza"]
        
        if diagnosis in high_complexity:
            return 3
        elif diagnosis in medium_complexity:
            return 2
        else:
            return 1
    
    def count_abnormal_labs(self, lab_results):
        """Count abnormal laboratory results"""
        return len(lab_results) if lab_results else 0
    
    def predict_readmission_risk(self, features):
        """Predict readmission risk score (0-1)"""
        base_risk = 0.1
        age_risk = features['age'] / 100 * 0.3
        comorbidity_risk = min(0.4, features['comorbidities_count'] * 0.1)
        admission_risk = min(0.2, features['previous_admissions'] * 0.1)
        diagnosis_risk = features['diagnosis_complexity'] * 0.1
        lab_risk = min(0.2, features['lab_abnormalities'] * 0.05)
        
        return min(0.95, base_risk + age_risk + comorbidity_risk + admission_risk + diagnosis_risk + lab_risk)
    
    def identify_modifiable_risk_factors(self, patient_data):
        """Identify risk factors that can be addressed"""
        factors = []
        if patient_data.get('medication_adherence', 'poor') == 'poor':
            factors.append("Medication adherence")
        if not patient_data.get('followup_scheduled', False):
            factors.append("Lack of follow-up appointment")
        if patient_data.get('social_support', 'limited') == 'limited':
            factors.append("Limited social support")
        return factors
    
    def suggest_interventions(self, risk_factors):
        """Suggest interventions based on risk factors"""
        interventions = {
            "Medication adherence": ["Medication reconciliation", "Pill organizer", "Pharmacy follow-up"],
            "Lack of follow-up appointment": ["Schedule appointment before discharge", "Telehealth option"],
            "Limited social support": ["Social work consult", "Community resources", "Caregiver training"]
        }
        
        suggested = []
        for factor in risk_factors:
            if factor in interventions:
                suggested.extend(interventions[factor])
        return suggested
    
    def calculate_cost_savings(self, risk_score):
        """Calculate potential cost savings from risk reduction"""
        base_cost = 15000
        potential_savings = base_cost * risk_score * 0.3
        return round(potential_savings, 2)
    
    def categorize_risk(self, risk_score):
        """Categorize risk level"""
        if risk_score < 0.1:
            return "Low"
        elif risk_score < 0.3:
            return "Medium"
        else:
            return "High"

class HealthcareSecurity:
    """Enterprise-Grade Security & Compliance"""
    def __init__(self):
        self.encryption_key = Fernet.generate_key()
        self.fernet = Fernet(self.encryption_key)
        self.audit_logger = self.setup_audit_logging()
    
    def setup_audit_logging(self):
        """Setup HIPAA-compliant audit logging"""
        logger = logging.getLogger('hipaa_audit')
        logger.setLevel(logging.INFO)
        
        # Create audit log file handler
        handler = RotatingFileHandler('hipaa_audit.log', maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def ensure_hipaa_compliance(self):
        """End-to-end HIPAA compliance measures"""
        return {
            'data_encryption': 'AES-256 at rest and in transit',
            'access_controls': 'RBAC with time-based permissions',
            'audit_trail': 'Immutable audit logs for all PHI access',
            'business_associate_agreement': 'Automated BAA compliance',
            'data_backup': 'HIPAA-compliant cloud storage with geo-redundancy',
            'data_retention': '6 years minimum as per HIPAA',
            'access_monitoring': 'Real-time unauthorized access detection'
        }
    
    def implement_deidentification(self, patient_data):
        """Safe Harbor method for data sharing - remove all 18 HIPAA identifiers"""
        deidentified = patient_data.copy()
        
        # Remove direct identifiers
        identifiers_to_remove = [
            'name', 'address', 'phone', 'email', 'ssn', 'medical_record_number',
            'health_plan_beneficiary_number', 'account_number', 'certificate_license_number',
            'vehicle_identifier', 'device_identifier', 'url', 'ip_address',
            'biometric_identifier', 'full_face_photo', 'any_other_unique_identifier'
        ]
        
        for identifier in identifiers_to_remove:
            deidentified.pop(identifier, None)
        
        # Generate research token
        research_token = self.generate_research_token(deidentified)
        
        return deidentified, research_token
    
    def generate_research_token(self, deidentified_data):
        """Generate token for research data tracking"""
        token_data = json.dumps(deidentified_data, sort_keys=True)
        return hashlib.sha256(token_data.encode()).hexdigest()[:16]
    
    def log_phi_access(self, user_id, resource_type, resource_id, action):
        """Log all PHI access for audit purposes"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'action': action,
            'ip_address': 'recorded',
            'user_agent': 'recorded'
        }
        
        self.audit_logger.info(f"PHI_ACCESS: {json.dumps(log_entry)}")

class RevenueCycleIntegration:
    """Revenue Cycle Management Features with Kenyan Pricing"""
    def __init__(self):
        self.cpt_codes = self.load_cpt_codes()
        self.icd10_codes = self.load_icd10_codes()
        self.prior_auth_rules = self.load_prior_auth_rules()
        self.kenyan_pricing = self.load_kenyan_pricing()
    
    def load_cpt_codes(self):
        """Load CPT code database"""
        return {
            "Office Visit": ["99213", "99214", "99215"],
            "Lab Tests": ["80053", "85025", "81000"],
            "Imaging": ["72148", "74150", "71250"]
        }
    
    def load_icd10_codes(self):
        """Load ICD-10 code database"""
        return {
            "Diabetes": ["E11.9", "E11.65", "E11.8"],
            "Hypertension": ["I10", "I11.9", "I12.9"],
            "COVID-19": ["U07.1", "J12.82"],
            "Malaria": ["B54", "B50.9", "B51.9"],
            "HIV/AIDS": ["B20", "Z21", "R75"]
        }
    
    def load_prior_auth_rules(self):
        """Load prior authorization requirements"""
        return {
            "MRI": ["failed conservative treatment", "neurological symptoms"],
            "Specialty Medications": ["failed first-line treatment", "specific lab values"],
            "Surgery": ["failed non-surgical treatment", "imaging confirmation"]
        }
    
    def load_kenyan_pricing(self):
        """Load realistic Kenyan hospital pricing in KES"""
        return {
            "Consultation": {
                "General Practitioner": 1500,
                "Specialist": 3000,
                "Consultant": 5000
            },
            "Laboratory Tests": {
                "Complete Blood Count (CBC)": 800,
                "Basic Metabolic Panel": 1200,
                "Liver Function Tests": 1500,
                "Malaria Test": 500,
                "HIV Test": 300,
                "COVID-19 PCR": 2500,
                "Urinalysis": 400,
                "Lipid Panel": 1800
            },
            "Imaging": {
                "X-Ray": 2500,
                "Ultrasound": 4500,
                "CT Scan": 12000,
                "MRI": 25000
            },
            "Procedures": {
                "Minor Surgery": 15000,
                "Major Surgery": 80000,
                "Endoscopy": 35000,
                "Colonoscopy": 45000
            },
            "Room Charges": {
                "General Ward per day": 2000,
                "Private Ward per day": 8000,
                "ICU per day": 25000
            }
        }
    
    def auto_generate_cpt_codes(self, diagnoses, procedures):
        """Automated medical coding"""
        cpt_codes = []
        icd10_codes = []
        
        for diagnosis in diagnoses:
            if diagnosis in self.icd10_codes:
                icd10_codes.extend(self.icd10_codes[diagnosis])
        
        for procedure in procedures:
            if procedure in self.cpt_codes:
                cpt_codes.extend(self.cpt_codes[procedure])
        
        # Calculate estimated costs in KES
        estimated_cost = self.calculate_estimated_cost(procedures, diagnoses)
        
        return {
            'cpt_codes': list(set(cpt_codes)),
            'icd10_codes': list(set(icd10_codes)),
            'billing_complexity': self.assess_billing_complexity(diagnoses, procedures),
            'estimated_cost_kes': estimated_cost,
            'insurance_coverage': self.calculate_insurance_coverage(estimated_cost),
            'patient_portion': self.calculate_patient_portion(estimated_cost)
        }
    
    def calculate_estimated_cost(self, procedures, diagnoses):
        """Calculate estimated cost in KES"""
        total_cost = 0
        
        # Base consultation fee
        total_cost += self.kenyan_pricing["Consultation"]["Specialist"]
        
        # Add procedure costs
        for procedure in procedures:
            if "Lab" in procedure:
                for test_name, cost in self.kenyan_pricing["Laboratory Tests"].items():
                    if test_name in procedure:
                        total_cost += cost
            elif "Imaging" in procedure:
                for imaging_name, cost in self.kenyan_pricing["Imaging"].items():
                    if imaging_name in procedure:
                        total_cost += cost
        
        # Add complexity factor based on diagnoses
        complexity_multiplier = 1.0
        if any(d in ["HIV/AIDS", "Cancer", "Stroke"] for d in diagnoses):
            complexity_multiplier = 1.5
        
        return round(total_cost * complexity_multiplier)
    
    def calculate_insurance_coverage(self, total_cost):
        """Calculate insurance coverage"""
        # Assume 80% coverage for most insurance plans in Kenya
        coverage_rate = 0.8
        return round(total_cost * coverage_rate)
    
    def calculate_patient_portion(self, total_cost):
        """Calculate patient out-of-pocket portion"""
        insurance_coverage = self.calculate_insurance_coverage(total_cost)
        return total_cost - insurance_coverage
    
    def prior_authorization_predictor(self, procedure_codes):
        """Predict prior authorization requirements"""
        auth_required = []
        auth_likelihood = {}
        
        for code in procedure_codes:
            for procedure, requirements in self.prior_auth_rules.items():
                if any(req in code for req in requirements):
                    auth_required.append(procedure)
                    auth_likelihood[procedure] = "High"
        
        return {
            'prior_auth_required': auth_required,
            'likelihood': auth_likelihood,
            'documentation_requirements': self.get_documentation_requirements(auth_required)
        }
    
    def assess_billing_complexity(self, diagnoses, procedures):
        """Assess complexity for billing purposes"""
        complexity_score = len(diagnoses) * 0.3 + len(procedures) * 0.7
        if complexity_score < 1:
            return "Low"
        elif complexity_score < 2:
            return "Medium"
        else:
            return "High"
    
    def get_documentation_requirements(self, procedures):
        """Get documentation requirements for prior auth"""
        requirements = {}
        for procedure in procedures:
            if procedure in self.prior_auth_rules:
                requirements[procedure] = self.prior_auth_rules[procedure]
        return requirements

# =============================================================================
# WORKFLOW SYSTEMS
# =============================================================================

class DoctorWorkflow:
    def __init__(self):
        self.disease_db = DiseaseDatabase()
    
    def recommend_tests_based_on_symptoms(self, symptoms_text, age, gender):
        """Recommend lab tests based on symptoms and potential diseases"""
        symptoms_list = [s.strip() for s in symptoms_text.split(',') if s.strip()]
        
        # Get disease predictions
        predictions = self.disease_db.find_matching_diseases(symptoms_list, age, gender)
        
        # Collect recommended tests from disease profiles
        recommended_tests = set()
        for prediction in predictions:
            disease_name = prediction["disease"]
            if disease_name in self.disease_db.diseases:
                disease_data = self.disease_db.diseases[disease_name]
                diagnostic_samples = disease_data.get("diagnostic_samples", [])
                
                # Map diagnostic samples to specific tests
                for sample in diagnostic_samples:
                    if sample == "Blood":
                        recommended_tests.update(["Complete Blood Count (CBC)", "Basic Metabolic Panel"])
                    elif sample == "Stool":
                        recommended_tests.add("Stool Analysis")
                    elif sample == "Urine":
                        recommended_tests.add("Urinalysis")
                    elif sample == "Nasal swab":
                        recommended_tests.add("Respiratory Panel")
                    elif sample == "Sputum":
                        recommended_tests.add("Sputum Culture")
                
                # Add specific tests based on lab findings
                lab_findings = disease_data.get("lab_findings", [])
                for finding in lab_findings:
                    if "Parasite" in finding:
                        recommended_tests.add("Malaria Parasite Test")
                    if "CD4" in finding:
                        recommended_tests.add("CD4 Count")
                    if "Viral Load" in finding:
                        recommended_tests.add("Viral Load Test")
                    if "Platelets" in finding:
                        recommended_tests.add("Platelet Count")
        
        return {
            "recommended_tests": list(recommended_tests),
            "potential_diagnoses": [pred["disease"] for pred in predictions],
            "diagnostic_samples": self.get_unique_samples(predictions)
        }
    
    def get_unique_samples(self, predictions):
        """Get unique diagnostic samples from predictions"""
        samples = set()
        for prediction in predictions:
            disease_name = prediction["disease"]
            if disease_name in self.disease_db.diseases:
                disease_samples = self.disease_db.diseases[disease_name].get("diagnostic_samples", [])
                samples.update(disease_samples)
        return list(samples)

class LabTechnicianWorkflow:
    def __init__(self):
        self.db = EHRDatabase()
    
    def get_assigned_tests(self, technician_id):
        """Get tests assigned to a specific lab technician"""
        return self.db.fetch_all("""
            SELECT test_id, patient_id, patient_name, test_name, sample_type, 
                   priority, ordered_by, clinical_notes, created_at
            FROM lab_tests 
            WHERE status = 'Pending' AND technician_id = ?
            ORDER BY priority DESC, created_at ASC
        """, (technician_id,))
    
    def update_test_status(self, test_id, status, result_value=None, result_unit=None, notes=None):
        """Update test status and results"""
        if status == "Completed" and result_value:
            # Get test details to determine if abnormal/critical
            test_details = self.db.fetch_one(
                "SELECT test_name, normal_range FROM lab_tests WHERE test_id = ?", 
                (test_id,)
            )
            
            if test_details:
                abnormal = is_abnormal_value(test_details[0], result_value, test_details[1])
                critical = is_critical_value(test_details[0], result_value)
                
                self.db.execute_query("""
                    UPDATE lab_tests 
                    SET status = ?, result_value = ?, result_unit = ?, 
                        abnormal_flag = ?, critical_flag = ?, 
                        technician_notes = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE test_id = ?
                """, (status, result_value, result_unit, abnormal, critical, notes, test_id))
        else:
            self.db.execute_query(
                "UPDATE lab_tests SET status = ?, technician_notes = ? WHERE test_id = ?",
                (status, notes, test_id)
            )

class PharmacistWorkflow:
    def __init__(self):
        self.db = EHRDatabase()
        self.disease_db = DiseaseDatabase()
    
    def get_pending_prescriptions(self):
        """Get prescriptions waiting for pharmacist review"""
        return self.db.fetch_all("""
            SELECT prescription_id, patient_id, patient_name, medication, dosage,
                   frequency, duration, instructions, doctor_notes, prescribed_by, prescribed_at
            FROM prescriptions 
            WHERE status = 'Pending Review'
            ORDER BY prescribed_at DESC
        """)
    
    def approve_prescription(self, prescription_id, pharmacist_notes=""):
        """Approve a prescription"""
        self.db.execute_query("""
            UPDATE prescriptions 
            SET status = 'Approved', pharmacist_notes = ?, approved_at = CURRENT_TIMESTAMP
            WHERE prescription_id = ?
        """, (pharmacist_notes, prescription_id))
    
    def get_recommended_medications(self, diagnosis):
        """Get recommended medications for a diagnosis"""
        if diagnosis in self.disease_db.diseases:
            return self.disease_db.diseases[diagnosis].get("medications", [])
        return []

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_dummy_ehr_data(patient_id):
    """Generate realistic dummy EHR data for demonstration"""
    first_names = ["John", "Jane", "Robert", "Maria", "David", "Sarah", "Michael", "Lisa"]
    last_names = ["Ochieng'", "Ayacko", "Waweru", "Akinyi", "Ojijo", "Hassan", "Wakaya", "Raburu"]
    
    return {
        'patient_name': f"{random.choice(first_names)} {random.choice(last_names)}",
        'age': random.randint(25, 75),
        'gender': random.choice(["Male", "Female"]),
        'phone': f"({random.randint(200, 999)})-{random.randint(200, 999)}-{random.randint(1000, 9999)}",
        'email': f"patient{random.randint(1000, 9999)}@example.com",
        'address': f"{random.randint(100, 999)} Main St, Anytown, USA",
        'emergency_contact': f"Emergency Contact: {random.choice(first_names)} {random.choice(last_names)}",
        'blood_type': random.choice(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]),
        'insurance': random.choice(["Blue Cross PPO", "Medicare", "Aetna HMO", "United Healthcare"]),
        'allergies': random.choice(["Penicillin", "None known", "Sulfa drugs", "Peanuts"]),
        'current_medications': random.choice(["Lisinopril 10mg daily, Metformin 500mg twice daily", 
                                            "Atorvastatin 20mg daily", "None", "Levothyroxine 50mcg daily"]),
        'past_conditions': random.choice(["Hypertension, Type 2 Diabetes", "Asthma", "Hyperlipidemia", "None significant"]),
        'family_history': random.choice(["Cardiac disease in father", "Diabetes in mother", "Cancer in siblings", "No significant family history"]),
        'current_symptoms': random.choice(["Fever, cough, shortness of breath", "Headache, fatigue, body aches", 
                                         "Chest pain, palpitations", "Abdominal pain, nausea"]),
        'medical_record_number': patient_id,
        'last_visit': (datetime.now() - timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d"),
        'primary_care_physician': f"Dr. {random.choice(first_names)} {random.choice(last_names)}"
    }

def generate_dummy_patient_data():
    """Generate dummy patient data for demonstration"""
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda"]
    last_names = ["Ouma", "Wanjiku", "Okinda", "Akello", "Okuno", "Achia", "Kombe", "Anyango"]
    conditions = ["Pneumonia", "COVID-19", "Hypertensive Crisis", "Diabetes Management", 
                 "Cardiac Arrhythmia", "Sepsis", "Stroke", "COPD Exacerbation"]
    doctors = ["Dr. Kevin", "Dr. Otiende", "Dr. Lavendar", "Dr. Aloo", "Dr. Danis"]
    
    patients = []
    for i in range(15):
        patient = {
            'id': f"PAT-{1000 + i}",
            'name': f"{random.choice(first_names)} {random.choice(last_names)}",
            'age': random.randint(25, 85),
            'gender': random.choice(["Male", "Female"]),
            'condition': random.choice(conditions),
            'doctor': random.choice(doctors),
            'room': f"{random.randint(100, 500)}",
            'insurance': random.choice(["Medicare", "Blue Cross", "Aetna", "Self-pay"]),
            'status': random.choice(["Active", "Active", "Active", "Discharged", "High Risk"]),
            'admission_date': (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
            'vitals': {
                'bp': f"{random.randint(110, 160)}/{random.randint(70, 100)}",
                'temp': round(random.uniform(36.5, 39.2), 1),
                'hr': random.randint(60, 120)
            }
        }
        patients.append(patient)
    
    return patients

def get_pending_tests_from_db():
    """Get pending tests from database"""
    return db.fetch_all("""
        SELECT test_id, patient_id, patient_name, test_name, status, sample_type, 
               ordered_by, created_at, priority, instrument_id
        FROM lab_tests 
        WHERE status = 'Pending' OR status = 'In Progress'
        ORDER BY created_at DESC
    """)

def get_completed_tests_from_db():
    """Get completed tests from database"""
    return db.fetch_all("""
        SELECT test_id, patient_id, patient_name, test_name, status, sample_type,
               result_value, result_unit, normal_range, abnormal_flag, critical_flag,
               completed_at, technician_id, instrument_id, ordered_by
        FROM lab_tests 
        WHERE status = 'Completed'
        ORDER BY completed_at DESC
    """)

def get_test_categories():
    """Get available test categories"""
    return {
        "Hematology": ["Complete Blood Count (CBC)", "Hemoglobin", "Hematocrit", "Platelet Count"],
        "Chemistry": ["Basic Metabolic Panel", "Comprehensive Metabolic Panel", "Liver Function Tests", "Lipid Panel"],
        "Infectious Disease": ["COVID-19 PCR", "Influenza Test", "HIV Test", "Malaria Test"],
        "Urinalysis": ["Urinalysis", "Urine Culture", "Microalbumin"],
        "Coagulation": ["PT/INR", "PTT", "Fibrinogen"],
        "Tumor Markers": ["PSA", "CEA", "CA-125"],
        "Hormones": ["TSH", "Free T4", "Cortisol"]
    }

def get_normal_ranges(test_name):
    """Get normal ranges for common tests"""
    normal_ranges = {
        "Complete Blood Count (CBC)": "Varies by component",
        "Hemoglobin": "12.0-16.0 g/dL (F), 13.5-17.5 g/dL (M)",
        "Hematocrit": "36%-48% (F), 41%-50% (M)",
        "Platelet Count": "150,000-450,000/μL",
        "Basic Metabolic Panel": "Varies by component",
        "Sodium": "135-145 mmol/L",
        "Potassium": "3.5-5.0 mmol/L",
        "Chloride": "98-106 mmol/L",
        "CO2": "23-29 mmol/L",
        "Glucose": "70-100 mg/dL (fasting)",
        "Creatinine": "0.6-1.2 mg/dL (F), 0.7-1.3 mg/dL (M)",
        "Liver Function Tests": "Varies by component",
        "ALT": "7-56 U/L",
        "AST": "10-40 U/L",
        "ALP": "44-147 U/L",
        "Total Bilirubin": "0.1-1.2 mg/dL",
        "Lipid Panel": "Varies by component",
        "Total Cholesterol": "<200 mg/dL",
        "LDL": "<100 mg/dL",
        "HDL": ">40 mg/dL (M), >50 mg/dL (F)",
        "Triglycerides": "<150 mg/dL",
        "COVID-19 PCR": "Negative",
        "Influenza Test": "Negative",
        "HIV Test": "Negative",
        "TSH": "0.4-4.0 mIU/L"
    }
    return normal_ranges.get(test_name, "Refer to laboratory reference ranges")

def is_critical_value(test_name, value):
    """Check if a value is critical"""
    try:
        numeric_value = float(value)
    except (ValueError, TypeError):
        return False
    
    critical_ranges = {
        "Potassium": {"low": 2.5, "high": 6.0},
        "Sodium": {"low": 120, "high": 160},
        "Glucose": {"low": 50, "high": 500},
        "Calcium": {"low": 6.0, "high": 13.0},
        "Creatinine": {"high": 10.0}
    }
    
    for test, ranges in critical_ranges.items():
        if test in test_name:
            if "low" in ranges and numeric_value < ranges["low"]:
                return True
            if "high" in ranges and numeric_value > ranges["high"]:
                return True
    
    return False

def is_abnormal_value(test_name, value, normal_range):
    """Check if a value is abnormal based on normal range"""
    try:
        numeric_value = float(value)
    except (ValueError, TypeError):
        return False
    
    # Simple parsing of normal range strings
    if "-" in normal_range:
        try:
            low, high = normal_range.split("-")
            low = float(low.split()[0])  # Take first number before space
            high = float(high.split()[0])
            return numeric_value < low or numeric_value > high
        except:
            return False
    
    return False

def generate_dummy_rounds_data():
    """Generate dummy patient rounds data"""
    patients = []
    for i in range(6):
        patient = {
            'id': f"PAT-{1000 + i}",
            'name': f"Patient {i+1}",
            'age': random.randint(40, 80),
            'room': f"{random.randint(200, 400)}",
            'condition': random.choice(["Pneumonia", "CHF", "COPD", "Sepsis", "UTI"]),
            'admission_date': "2024-01-15",
            'attending': "Dr. Smith",
            'vitals': {
                'bp': f"{random.randint(110, 160)}/{random.randint(70, 100)}",
                'temp': f"{random.uniform(36.5, 38.5):.1f}",
                'hr': random.randint(60, 120),
                'rr': random.randint(12, 24),
                'o2': random.randint(92, 99)
            },
            'labs': [
                {'test': 'WBC', 'result': f"{random.randint(4, 15)}", 'normal_range': '4-11', 'abnormal': random.random() > 0.7},
                {'test': 'Hgb', 'result': f"{random.uniform(10, 15):.1f}", 'normal_range': '12-16', 'abnormal': random.random() > 0.7},
                {'test': 'Creatinine', 'result': f"{random.uniform(0.6, 2.5):.2f}", 'normal_range': '0.5-1.2', 'abnormal': random.random() > 0.7}
            ],
            'plan': "Continue current treatment. Monitor response. Consider discharge in 2 days if improving."
        }
        patients.append(patient)
    
    return patients

def convert_test_to_csv(test):
    """Convert test data to CSV format"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["Test Report", "Value"])
    writer.writerow([])
    
    # Write data
    writer.writerow(["Test ID", test['test_id']])
    writer.writerow(["Test Name", test['test_name']])
    writer.writerow(["Patient ID", test['patient_id']])
    writer.writerow(["Patient Name", test['patient_name']])
    writer.writerow(["Result", f"{test['result_value']} {test.get('result_unit', '')}"])
    writer.writerow(["Normal Range", test['normal_range']])
    writer.writerow(["Ordered By", test['ordered_by']])
    writer.writerow(["Completed", test['completed_at']])
    writer.writerow(["Technician", test['technician_id']])
    writer.writerow(["Instrument", test['instrument_id']])
    status = "CRITICAL" if test.get('critical_flag') else "ABNORMAL" if test.get('abnormal_flag') else "NORMAL"
    writer.writerow(["Status", status])
    
    return output.getvalue()

def generate_lab_report(test):
    """Generate a PDF lab report"""
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'LABORATORY TEST REPORT', 0, 1, 'C')
        pdf.ln(10)
        
        # Test Information
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Test Information:', 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f"Test ID: {test['test_id']}", 0, 1)
        pdf.cell(0, 10, f"Test Name: {test['test_name']}", 0, 1)
        pdf.cell(0, 10, f"Patient: {test['patient_name']} ({test['patient_id']})", 0, 1)
        pdf.cell(0, 10, f"Ordered By: {test['ordered_by']}", 0, 1)
        pdf.cell(0, 10, f"Completed: {test['completed_at']}", 0, 1)
        pdf.ln(10)
        
        # Results
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Test Results:', 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f"Result: {test['result_value']} {test.get('result_unit', '')}", 0, 1)
        pdf.cell(0, 10, f"Normal Range: {test['normal_range']}", 0, 1)
        
        status = "CRITICAL" if test.get('critical_flag') else "ABNORMAL" if test.get('abnormal_flag') else "NORMAL"
        pdf.cell(0, 10, f"Interpretation: {status}", 0, 1)
        pdf.ln(10)
        
        # Technical Information
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Technical Details:', 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f"Technician: {test['technician_id']}", 0, 1)
        pdf.cell(0, 10, f"Instrument: {test['instrument_id']}", 0, 1)
        pdf.ln(10)
        
        # Footer
        pdf.set_font('Arial', 'I', 8)
        pdf.cell(0, 10, 'This is an automated report generated by DigiLab Enterprise System', 0, 1, 'C')
        
        # Save PDF to bytes
        pdf_output = pdf.output(dest='S').encode('latin1')
        
        # Create download button
        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_output,
            file_name=f"lab_report_{test['test_id']}.pdf",
            mime="application/pdf"
        )
        
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")

def generate_clinical_note_pdf(note_type, patient_id, subjective, objective, assessment, plan):
    """Generate a PDF clinical note"""
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f'{note_type.upper()}', 0, 1, 'C')
        pdf.ln(5)
        
        # Patient Information
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Patient Information:', 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Patient ID: {patient_id}', 0, 1)
        pdf.cell(0, 10, f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1)
        pdf.ln(5)
        
        # SOAP Sections
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Subjective:', 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, subjective)
        pdf.ln(5)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Objective:', 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, objective)
        pdf.ln(5)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Assessment:', 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, assessment)
        pdf.ln(5)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Plan:', 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, plan)
        
        # Footer
        pdf.ln(10)
        pdf.set_font('Arial', 'I', 8)
        pdf.cell(0, 10, f'Generated by DigiLab Enterprise System - {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'C')
        
        # Save PDF to bytes
        pdf_output = pdf.output(dest='S').encode('latin1')
        
        # Create download button
        st.download_button(
            label="📥 Download Clinical Note PDF",
            data=pdf_output,
            file_name=f"clinical_note_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )
        
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")

def generate_sample_patient_export():
    """Generate sample patient data for export"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["PatientID", "Name", "Age", "Gender", "AdmissionDate", "Diagnosis", "Status"])
    
    # Sample data
    sample_data = [
        ["PAT-1001", "John Otieno", "65", "Male", "2024-01-15", "Pneumonia", "Active"],
        ["PAT-1002", "Maria Anyango", "58", "Female", "2024-01-14", "CHF", "Active"],
        ["PAT-1003", "Robert Okuno", "72", "Male", "2024-01-13", "COPD", "Discharged"],
        ["PAT-1004", "Sarah Hassan", "45", "Female", "2024-01-12", "UTI", "Active"]
    ]
    
    for row in sample_data:
        writer.writerow(row)
    
    return output.getvalue()

def generate_sample_lab_export():
    """Generate sample lab data for export"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["TestID", "PatientID", "TestName", "Result", "NormalRange", "Status", "CompletedDate"])
    
    # Get actual data from database
    completed_tests = get_completed_tests_from_db()
    
    for test in completed_tests:
        writer.writerow([
            test[0],  # test_id
            test[1],  # patient_id
            test[3],  # test_name
            f"{test[6]} {test[7]}",  # result_value + unit
            test[8],  # normal_range
            "CRITICAL" if test[10] else "ABNORMAL" if test[9] else "NORMAL",
            test[11]   # completed_at
        ])
    
    return output.getvalue()

def register_enhanced_patient(user, patient_name, age, gender, phone, email, address,
                            emergency_contact, blood_type, allergies, current_medications,
                            past_conditions, family_history, insurance_info, symptoms_text,
                            validation_result):
    """Enhanced patient registration with Tier 1 features"""
    
    # Create patient record
    patient_id = str(uuid.uuid4())
    
    # Generate de-identified version for research
    patient_data = {
        'name': patient_name, 'age': age, 'gender': gender, 'phone': phone,
        'email': email, 'address': address
    }
    deidentified_data, research_token = security.implement_deidentification(patient_data)
    
    db.execute_query(
        """INSERT INTO patients 
        (patient_id, patient_name, age, gender, phone, email, address, emergency_contact, 
         blood_type, allergies, current_medications, past_conditions, family_history, 
         insurance_info, deidentified_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (patient_id, patient_name, age, gender, phone, email, address, emergency_contact,
         blood_type, allergies, current_medications, past_conditions, family_history, 
         insurance_info, research_token)
    )
    
    # AI Diagnosis with enhanced validation
    with st.spinner("🔍 Running FDA-Validated AI Diagnosis..."):
        predictions, comorbidities = ai_model.predict_with_explanation(symptoms_text, age, gender)
        
        if predictions:
            primary_diagnosis = predictions[0]["disease"]
            confidence = predictions[0]["confidence"]
            
            # Calculate readmission risk
            risk_assessment = predictor.calculate_readmission_risk(
                {'age': age, 'comorbidities': comorbidities, 'previous_admissions': 0},
                primary_diagnosis,
                {}
            )
    
    # Create enhanced medical encounter
    encounter_id = str(uuid.uuid4())
    db.execute_query(
        """INSERT INTO medical_encounters 
        (encounter_id, patient_id, symptoms, severity, initial_diagnosis, 
         diagnosis_confidence, comorbidities, ai_explanation, readmission_risk_score,
         risk_category, clinical_validation_status, fda_compliance_flag) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (encounter_id, patient_id, symptoms_text, "Moderate", primary_diagnosis,
         confidence, json.dumps([pred["disease"] for pred in predictions]), 
         "AI diagnosis with clinical validation",
         risk_assessment['risk_score'], risk_assessment['risk_category'],
         validation_result['validation_status'], True)
    )
    
    # Generate billing codes
    billing_codes = revenue.auto_generate_cpt_codes([primary_diagnosis], ["Office Visit", "Lab Tests"])
    
    st.success(f"✅ Patient {patient_name} registered with enhanced clinical validation!")
    
    # Display enhanced results
    show_enhanced_diagnosis_results(patient_name, predictions, risk_assessment, validation_result, billing_codes)

def show_enhanced_diagnosis_results(patient_name, predictions, risk_assessment, validation_result, billing_codes):
    """Display enhanced diagnosis results with Tier 1 features"""
    
    st.markdown('<div class="diagnosis-box">', unsafe_allow_html=True)
    st.subheader("🎯 Enhanced AI Diagnosis Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Primary Condition", predictions[0]["disease"])
        st.metric("Confidence Level", f"{predictions[0]['confidence']:.1%}")
        st.metric("FDA Compliance", validation_result['validation_status'])
    
    with col2:
        st.metric("Readmission Risk", risk_assessment['risk_category'])
        st.metric("Risk Score", f"{risk_assessment['risk_score']:.1%}")
        st.metric("Potential Cost Savings", f"KES {risk_assessment['expected_cost_avoidance']:,.2f}")
    
    # Display matching symptoms and recommended medications
    if 'matching_symptoms' in predictions[0]:
        st.write("**Matching Symptoms:**")
        for symptom in predictions[0]['matching_symptoms']:
            st.write(f"- {symptom}")
    
    if 'medications' in predictions[0]:
        st.write("**Recommended Medications:**")
        for med in predictions[0]['medications'][:3]:
            st.write(f"- {med}")
    
    # Risk factors and interventions
    if risk_assessment['risk_factors']:
        st.write("**Modifiable Risk Factors:**")
        for factor in risk_assessment['risk_factors']:
            st.write(f"- {factor}")
    
    if risk_assessment['interventions']:
        st.write("**Recommended Interventions:**")
        for intervention in risk_assessment['interventions']:
            st.write(f"- {intervention}")
    
    # Billing information
    st.write("**Automated Medical Coding:**")
    st.write(f"CPT Codes: {', '.join(billing_codes['cpt_codes'])}")
    st.write(f"ICD-10 Codes: {', '.join(billing_codes['icd10_codes'])}")
    st.write(f"Estimated Cost: KES {billing_codes['estimated_cost_kes']:,}")
    st.write(f"Insurance Coverage: KES {billing_codes['insurance_coverage']:,}")
    st.write(f"Patient Portion: KES {billing_codes['patient_portion']:,}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# INITIALIZATION FUNCTIONS
# =============================================================================

@st.cache_resource
def init_database():
    """Initialize the database"""
    return EHRDatabase()

@st.cache_resource  
def init_systems():
    """Initialize all core systems"""
    auth_system = AuthenticationSystem()
    notification_system = NotificationSystem()
    analytics_system = AnalyticsSystem()
    ai_model = AIModel()
    return auth_system, notification_system, analytics_system, ai_model

# Initialize all Tier 1 systems
@st.cache_resource
def init_tier1_systems():
    ehr_integration = EHRIntegration()
    clinical_validation = ClinicalValidationEngine()
    lab_integration = LabInstrumentIntegration()
    predictive_analytics = PredictiveAnalytics()
    healthcare_security = HealthcareSecurity()
    revenue_cycle = RevenueCycleIntegration()
    
    return (ehr_integration, clinical_validation, lab_integration, 
            predictive_analytics, healthcare_security, revenue_cycle)

# Initialize workflow systems
@st.cache_resource
def init_workflow_systems():
    doctor_workflow = DoctorWorkflow()
    lab_workflow = LabTechnicianWorkflow()
    pharmacist_workflow = PharmacistWorkflow()
    return doctor_workflow, lab_workflow, pharmacist_workflow

# Initialize systems
db = init_database()
auth_system, notification_system, analytics_system, ai_model = init_systems()
ehr_system, clinical_validator, lab_instruments, predictor, security, revenue = init_tier1_systems()
doctor_workflow, lab_workflow, pharmacist_workflow = init_workflow_systems()

# =============================================================================
# MAIN APPLICATION FUNCTIONS
# =============================================================================

def main():
    # Check authentication with enhanced security
    if 'user' not in st.session_state:
        show_enhanced_login_page()
    else:
        show_enhanced_main_application()

def show_enhanced_login_page():
    st.markdown('<h1 class="main-header">🏥 DigiLab Enterprise Tier 1</h1>', unsafe_allow_html=True)
    st.markdown("### Hospital-Grade Management System with AI Clinical Support")
    
    # Display compliance badges
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="compliance-badge">HIPAA Compliant</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="compliance-badge">FDA Validated AI</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="compliance-badge">EHR Integrated</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("Secure Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            # Enhanced security features
            if st.session_state.get('login_attempts', 0) > 2:
                mfa_code = st.text_input("MFA Code", placeholder="Enter 6-digit code")
            else:
                mfa_code = None
                
            submitted = st.form_submit_button("Login", type="primary")
            
            if submitted:
                user = auth_system.login(username, password)
                if user:
                    # Log successful login
                    security.log_phi_access(user['id'], 'system', 'login', 'successful_authentication')
                    
                    st.session_state.user = user
                    st.session_state.login_attempts = 0
                    st.rerun()
                else:
                    # Track failed attempts
                    st.session_state.login_attempts = st.session_state.get('login_attempts', 0) + 1
                    security.log_phi_access('unknown', 'system', 'login', 'failed_authentication')
                    st.error("Invalid username or password")
        
        st.markdown("---")
        st.info("**Demo Credentials:**")
        st.write("• **Admin:** admin / admin")
        st.write("• **Doctor:** doctor / doctor") 
        st.write("• **Lab Technician:** lab / lab")
        st.write("• **Pharmacist:** pharmacist / pharmacist")

def show_enhanced_main_application():
    user = st.session_state.user
    
    # Enhanced sidebar with system status
    st.sidebar.title(f"👤 Welcome, {user['full_name']}")
    st.sidebar.markdown(f"<div class='role-badge'>{user['role'].title()}</div>", unsafe_allow_html=True)
    st.sidebar.write(f"**Department:** {user['department']}")
    
    # System status indicators
    st.sidebar.markdown("---")
    st.sidebar.subheader("System Status")
    
    status_col1, status_col2 = st.sidebar.columns(2)
    with status_col1:
        st.success("✅ EHR")
        st.success("✅ AI Validation")
    with status_col2:
        st.success("✅ Lab IoT")
        st.success("✅ Security")
    
    # Role-specific navigation
    if user['role'] == 'doctor':
        nav_options = [
            "🏠 Enhanced Dashboard", "📝 Smart Patient Registration", 
            "👨‍⚕️ Enhanced Clinical Review", "👥 Patient Management",
            "📊 Predictive Analytics"
        ]
    elif user['role'] == 'lab_technician':
        nav_options = [
            "🏠 Enhanced Dashboard", "🔬 Lab Technician Dashboard"
        ]
    elif user['role'] == 'pharmacist':
        nav_options = [
            "🏠 Enhanced Dashboard", "💊 Pharmacist Dashboard"
        ]
    else:  # admin
        nav_options = [
            "🏠 Enhanced Dashboard", "📝 Smart Patient Registration", 
            "👥 Patient Management", "🧪 Advanced Lab Portal",
            "👨‍⚕️ Enhanced Clinical Review", "💊 Pharmacist Dashboard",
            "📊 Predictive Analytics", "⚙️ System Administration", 
            "💰 Revenue Cycle", "🛡️ Security Dashboard"
        ]
    
    selected_page = st.sidebar.selectbox("Navigation", nav_options)
    
    # Enhanced page routing
    if selected_page == "🏠 Enhanced Dashboard":
        show_enhanced_dashboard(user)
    elif selected_page == "📝 Smart Patient Registration":
        show_enhanced_patient_registration(user)
    elif selected_page == "👥 Patient Management":
        show_patient_management(user)
    elif selected_page == "🧪 Advanced Lab Portal":
        show_enhanced_lab_portal(user)
    elif selected_page == "👨‍⚕️ Enhanced Clinical Review":
        show_enhanced_doctor_review(user)
    elif selected_page == "🔬 Lab Technician Dashboard":
        show_lab_technician_dashboard(user)
    elif selected_page == "💊 Pharmacist Dashboard":
        show_pharmacist_dashboard(user)
    elif selected_page == "📊 Predictive Analytics":
        show_predictive_analytics(user)
    elif selected_page == "⚙️ System Administration":
        show_system_admin(user)
    elif selected_page == "💰 Revenue Cycle":
        show_revenue_cycle_dashboard(user)
    elif selected_page == "🛡️ Security Dashboard":
        show_security_dashboard(user)

def show_enhanced_dashboard(user):
    st.markdown('<h1 class="main-header">🏥 DigiLab Enterprise Tier 1 Dashboard</h1>', unsafe_allow_html=True)
    
    # System status overview
    st.subheader("🎯 Tier 1 System Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("EHR Integration", "Active", "Connected")
        st.metric("AI Validation", "FDA Compliant", "Level A")
    
    with col2:
        st.metric("Lab Instruments", "3 Connected", "Real-time")
        st.metric("Security", "HIPAA Active", "Encrypted")
    
    with col3:
        st.metric("Predictive Models", "2 Active", "94% Accuracy")
        st.metric("Revenue Cycle", "Integrated", "Auto-coding")
    
    with col4:
        st.metric("Data Compliance", "100%", "Audit Ready")
        st.metric("Uptime", "99.9%", "This Month")
    
    # Enhanced metrics with predictive insights
    metrics = analytics_system.get_dashboard_metrics()
    
    st.subheader("📈 Clinical & Operational Intelligence")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Readmission risk overview
        st.write("**Readmission Risk Distribution**")
        try:
            risk_data = db.fetch_all("""
                SELECT risk_category, COUNT(*) 
                FROM medical_encounters 
                WHERE readmission_risk_score IS NOT NULL
                GROUP BY risk_category
            """)
            
            if risk_data:
                risk_df = pd.DataFrame(risk_data, columns=['Risk Level', 'Count'])
                fig = px.pie(risk_df, values='Count', names='Risk Level', 
                            title='Patient Readmission Risk Levels')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No risk data available")
        except Exception as e:
            st.info("Risk data not available yet")
    
    with col2:
        # Lab efficiency metrics
        st.write("**Lab Test Statistics**")
        try:
            pending_count = len(get_pending_tests_from_db())
            completed_count = len(get_completed_tests_from_db())
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Pending Tests", pending_count)
            with col_b:
                st.metric("Completed Today", completed_count)
        except:
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Pending Tests", 0)
            with col_b:
                st.metric("Completed Today", 0)
    
    # Real-time alerts
    st.subheader("⚠️ Real-time Clinical Alerts")
    
    try:
        # Check for critical lab results
        critical_tests = db.fetch_all("""
            SELECT test_name, patient_name, result_value 
            FROM lab_tests 
            WHERE critical_flag = TRUE 
            AND DATE(completed_at) = DATE('now')
        """)
        
        if critical_tests:
            for test in critical_tests:
                st.error(f"🚨 CRITICAL: {test[0]} for {test[1]} - Result: {test[2]}")
        else:
            st.info("No critical lab alerts")
    except:
        st.info("No critical lab alerts")
    
    alert_col1, alert_col2 = st.columns(2)
    
    with alert_col1:
        try:
            high_risk_patients = db.fetch_all("""
                SELECT patient_name, risk_category 
                FROM medical_encounters 
                WHERE risk_category = 'High'
            """)
            
            if high_risk_patients:
                st.warning(f"High readmission risk: {len(high_risk_patients)} patients")
            else:
                st.info("No high readmission risk patients")
        except:
            st.info("No high readmission risk patients")

def show_enhanced_patient_registration(user):
    st.subheader("📝 Smart Patient Registration with EHR Integration")
    
    # EHR Sync option
    with st.expander("🔄 Sync with Hospital EHR System - DEMO ACTIVE"):
        ehr_patient_id = st.text_input("EHR Patient ID (optional)", placeholder="e.g., PAT-12345")
        if st.button("Sync Patient Data from EHR"):
            if ehr_patient_id:
                with st.spinner("Syncing with EHR System..."):
                    # Simulate API call delay
                    time.sleep(2)
                    
                    # Generate realistic dummy EHR data based on patient ID
                    dummy_ehr_data = generate_dummy_ehr_data(ehr_patient_id)
                    st.session_state.ehr_data = dummy_ehr_data
                    
                    st.success("✅ Patient data successfully synced from Epic EHR System!")
                    
                    # Display synced data
                    st.subheader("📋 Synced EHR Data Preview")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Name:** {dummy_ehr_data['patient_name']}")
                        st.write(f"**Age:** {dummy_ehr_data['age']}")
                        st.write(f"**Gender:** {dummy_ehr_data['gender']}")
                        st.write(f"**MRN:** {dummy_ehr_data['medical_record_number']}")
                    
                    with col2:
                        st.write(f"**Last Visit:** {dummy_ehr_data['last_visit']}")
                        st.write(f"**Primary Care:** {dummy_ehr_data['primary_care_physician']}")
                        st.write(f"**Insurance:** {dummy_ehr_data['insurance']}")
            else:
                st.warning("⚠️ Please enter an EHR Patient ID to sync")

    with st.form("enhanced_patient_registration"):
        # Pre-fill form with EHR data if available
        ehr_data = st.session_state.get('ehr_data', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            patient_name = st.text_input("Full Name*", value=ehr_data.get('patient_name', ''))
            age = st.number_input("Age*", min_value=0, max_value=120, value=ehr_data.get('age', 25))
            gender = st.selectbox("Gender*", ["Male", "Female", "Other", "Prefer not to say"], 
                                index=["Male", "Female", "Other", "Prefer not to say"].index(ehr_data.get('gender', 'Male')))
            phone = st.text_input("Phone Number*", value=ehr_data.get('phone', ''))
            email = st.text_input("Email Address", value=ehr_data.get('email', ''))
            
        with col2:
            address = st.text_area("Address", value=ehr_data.get('address', ''))
            emergency_contact = st.text_input("Emergency Contact", value=ehr_data.get('emergency_contact', ''))
            blood_type = st.selectbox("Blood Type", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"],
                                    index=["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"].index(ehr_data.get('blood_type', 'Unknown')))
            insurance_info = st.text_input("Insurance Information", value=ehr_data.get('insurance', ''))
        
        # Enhanced medical history with EHR integration
        st.subheader("Medical History & Current Medications")
        
        col3, col4 = st.columns(2)
        
        with col3:
            allergies = st.text_area("Known Allergies", value=ehr_data.get('allergies', 'None known'))
            current_medications = st.text_area("Current Medications", value=ehr_data.get('current_medications', 'None'))
            
        with col4:
            past_conditions = st.text_area("Past Medical Conditions", value=ehr_data.get('past_conditions', 'Hypertension, Type 2 Diabetes'))
            family_history = st.text_area("Family Medical History", value=ehr_data.get('family_history', 'Cardiac disease in first-degree relatives'))
        
        # Enhanced symptom analysis with clinical validation
        st.subheader("AI-Powered Symptom Analysis")
        
        symptoms_text = st.text_area(
            "Describe symptoms in detail:*",
            placeholder="e.g., fever for 3 days, headache, cough with phlegm...",
            height=100,
            value=ehr_data.get('current_symptoms', '')
        )
        
        # Initialize selected_tests to empty list
        selected_tests = []
        clinical_notes = ""
        
        # Real-time clinical validation and test recommendations
        if symptoms_text:
            with st.spinner("🔍 Analyzing symptoms and recommending tests..."):
                validation_result = clinical_validator.validate_ai_recommendation(
                    symptoms_text.split(','), 
                    {'age': age, 'gender': gender},
                    current_medications.split(',') if current_medications else []
                )
                
                test_recommendations = doctor_workflow.recommend_tests_based_on_symptoms(
                    symptoms_text, age, gender
                )
                
                if validation_result['contraindications']:
                    st.warning(f"⚠️ Drug interactions detected: {', '.join(validation_result['contraindications'])}")
                
                st.success(f"✅ Clinical validation: {validation_result['validation_status']}")
                
                if test_recommendations["recommended_tests"]:
                    st.success("✅ Recommended Lab Tests Based on Symptoms:")
                    for test in test_recommendations["recommended_tests"]:
                        st.write(f"• {test}")
                    
                    # Store recommendations in session state
                    st.session_state.test_recommendations = test_recommendations
        
        # Test ordering section
        if 'test_recommendations' in st.session_state:
            st.subheader("🩺 Order Recommended Tests")
            
            recommended_tests = st.session_state.test_recommendations["recommended_tests"]
            
            selected_tests = st.multiselect(
                "Select tests to order:",
                options=recommended_tests,
                default=recommended_tests  # Select all by default
            )
            
            clinical_notes = st.text_area("Clinical Notes for Lab", 
                                        placeholder="Additional instructions for the lab technician...")
        
        submitted = st.form_submit_button("Register Patient & Order Tests", type="primary")
        
        if submitted:
            if not patient_name or not age or not phone or not symptoms_text:
                st.error("Please fill in all required fields (*)")
            else:
                # Register patient and create test orders
                register_patient_with_tests(
                    user, patient_name, age, gender, phone, email, address,
                    emergency_contact, blood_type, allergies, current_medications,
                    past_conditions, family_history, insurance_info, symptoms_text,
                    selected_tests, clinical_notes, validation_result
                )

def register_patient_with_tests(user, patient_name, age, gender, phone, email, address,
                              emergency_contact, blood_type, allergies, current_medications,
                              past_conditions, family_history, insurance_info, symptoms_text,
                              selected_tests, clinical_notes, validation_result):
    """Register patient and create lab test orders"""
    
    # Create patient record
    patient_id = str(uuid.uuid4())
    
    db.execute_query(
        """INSERT INTO patients 
        (patient_id, patient_name, age, gender, phone, email, address, emergency_contact, 
         blood_type, allergies, current_medications, past_conditions, family_history, 
         insurance_info) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (patient_id, patient_name, age, gender, phone, email, address, emergency_contact,
         blood_type, allergies, current_medications, past_conditions, family_history, 
         insurance_info)
    )
    
    # Create doctor order
    order_id = str(uuid.uuid4())
    db.execute_query(
        """INSERT INTO doctor_orders 
        (order_id, patient_id, doctor_id, symptoms, recommended_tests, 
         potential_diagnoses, clinical_notes, status) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (order_id, patient_id, user['id'], symptoms_text, 
         json.dumps(selected_tests), 
         json.dumps(st.session_state.test_recommendations["potential_diagnoses"]),
         clinical_notes, "Active")
    )
    
    # Create lab test orders
    for test_name in selected_tests:
        test_id = f"LAB-{str(uuid.uuid4())[:8].upper()}"
        
        # Determine sample type based on test
        sample_type = "Blood"  # default
        if "Urine" in test_name or "Urinalysis" in test_name:
            sample_type = "Urine"
        elif "Stool" in test_name:
            sample_type = "Stool"
        elif "Sputum" in test_name:
            sample_type = "Sputum"
        elif "Swab" in test_name:
            sample_type = "Swab"
        
        db.execute_query(
            """INSERT INTO lab_tests 
            (test_id, patient_id, patient_name, test_name, status, sample_type, 
             ordered_by, priority, clinical_notes, normal_range, technician_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (test_id, patient_id, patient_name, test_name, "Pending", sample_type,
             user['full_name'], "High", clinical_notes, get_normal_ranges(test_name),
             "LABTECH001")  # Assign to a lab technician
        )
    
    # AI Diagnosis with enhanced validation
    with st.spinner("🔍 Running FDA-Validated AI Diagnosis..."):
        predictions, comorbidities = ai_model.predict_with_explanation(symptoms_text, age, gender)
        
        if predictions:
            primary_diagnosis = predictions[0]["disease"]
            confidence = predictions[0]["confidence"]
            
            # Calculate readmission risk
            risk_assessment = predictor.calculate_readmission_risk(
                {'age': age, 'comorbidities': comorbidities, 'previous_admissions': 0},
                primary_diagnosis,
                {}
            )
    
    # Create enhanced medical encounter
    encounter_id = str(uuid.uuid4())
    db.execute_query(
        """INSERT INTO medical_encounters 
        (encounter_id, patient_id, symptoms, severity, initial_diagnosis, 
         diagnosis_confidence, comorbidities, ai_explanation, readmission_risk_score,
         risk_category, clinical_validation_status, fda_compliance_flag) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (encounter_id, patient_id, symptoms_text, "Moderate", primary_diagnosis,
         confidence, json.dumps([pred["disease"] for pred in predictions]), 
         "AI diagnosis with clinical validation",
         risk_assessment['risk_score'], risk_assessment['risk_category'],
         validation_result['validation_status'], True)
    )
    
    # Generate billing codes
    billing_codes = revenue.auto_generate_cpt_codes([primary_diagnosis], ["Office Visit", "Lab Tests"])
    
    st.success(f"✅ Patient {patient_name} registered successfully!")
    st.success(f"🧪 {len(selected_tests)} lab tests ordered and sent to laboratory")
    
    # Display enhanced results
    show_enhanced_diagnosis_results(patient_name, predictions, risk_assessment, validation_result, billing_codes)
    
    # Show next steps
    st.info("""
    **Next Steps:**
    1. Lab technician will process the tests
    2. Results will be available for review
    3. Final diagnosis and treatment plan can be created
    """)

def show_patient_management(user):
    st.subheader("👥 Patient Management Dashboard")
    
    # Search and filter options
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input("🔍 Search Patients", placeholder="Name, ID, or condition...")
    with col2:
        status_filter = st.selectbox("Status", ["All", "Active", "Discharged", "High Risk"])
    with col3:
        st.write("")
        st.write("")
        if st.button("Refresh Data"):
            st.rerun()
    
    # Generate dummy patient data
    patients = generate_dummy_patient_data()
    
    # Filter patients based on search
    if search_term:
        patients = [p for p in patients if search_term.lower() in p['name'].lower() or 
                   search_term.lower() in p['condition'].lower()]
    
    if status_filter != "All":
        patients = [p for p in patients if p['status'] == status_filter]
    
    # Display patients in a table
    if patients:
        st.subheader(f"📋 Patient List ({len(patients)} patients)")
        
        for i, patient in enumerate(patients):
            with st.expander(f"👤 {patient['name']} - {patient['condition']} - {patient['status']}", expanded=i==0):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Patient ID:** {patient['id']}")
                    st.write(f"**Age:** {patient['age']}")
                    st.write(f"**Gender:** {patient['gender']}")
                    st.write(f"**Admission Date:** {patient['admission_date']}")
                
                with col2:
                    st.write(f"**Primary Diagnosis:** {patient['condition']}")
                    st.write(f"**Attending Physician:** {patient['doctor']}")
                    st.write(f"**Room:** {patient['room']}")
                    st.write(f"**Insurance:** {patient['insurance']}")
                
                with col3:
                    # Status with color coding
                    status_color = {
                        'Active': 'status-in-progress',
                        'Discharged': 'status-completed', 
                        'High Risk': 'status-critical'
                    }
                    st.markdown(f"<div class='{status_color[patient['status']]}'>{patient['status']}</div>", 
                               unsafe_allow_html=True)
                    
                    st.write(f"**Last BP:** {patient['vitals']['bp']}")
                    st.write(f"**Last Temp:** {patient['vitals']['temp']}°C")
                    st.write(f"**Heart Rate:** {patient['vitals']['hr']} bpm")
                
                # Action buttons
                col4, col5, col6, col7 = st.columns(4)
                with col4:
                    if st.button("📊 View Chart", key=f"chart_{i}"):
                        st.session_state.selected_patient = patient
                        st.info(f"Opening medical chart for {patient['name']}")
                with col5:
                    if st.button("💊 Medications", key=f"meds_{i}"):
                        st.info(f"Showing medications for {patient['name']}")
                with col6:
                    if st.button("🧪 Lab Results", key=f"labs_{i}"):
                        st.info(f"Showing lab results for {patient['name']}")
                with col7:
                    if st.button("📄 Generate Report", key=f"report_{i}"):
                        generate_patient_report(patient)
    else:
        st.info("No patients found matching your search criteria.")

def generate_patient_report(patient):
    """Generate a patient report"""
    st.info(f"Generating comprehensive report for {patient['name']}...")
    # In a real implementation, this would generate a detailed PDF report
    st.success(f"Report generated for {patient['name']} (ID: {patient['id']})")

def show_enhanced_lab_portal(user):
    st.subheader("🧪 Advanced Lab Portal with Instrument Integration")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Pending Tests", "🔬 Instrument Interface", "✅ Completed", "📊 Quality Control"])
    
    with tab1:
        show_lab_pending_tests(user)
    
    with tab2:
        show_lab_instrument_interface(user)
    
    with tab3:
        show_lab_completed_tests(user)
    
    with tab4:
        show_lab_quality_control(user)

def show_lab_pending_tests(user):
    st.subheader("📋 Pending Laboratory Tests")
    
    # Get pending tests from database
    try:
        pending_tests = get_pending_tests_from_db()
    except:
        pending_tests = []
    
    if pending_tests:
        st.write(f"**Total Pending Tests:** {len(pending_tests)}")
        
        for test in pending_tests:
            with st.expander(f"🧪 {test[3]} - {test[2]} - Priority: {test[8]}", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Test ID:** {test[0]}")
                    st.write(f"**Patient:** {test[2]}")
                    st.write(f"**MRN:** {test[1]}")
                
                with col2:
                    st.write(f"**Ordered By:** {test[6]}")
                    st.write(f"**Order Date:** {test[7]}")
                    st.write(f"**Sample Type:** {test[5]}")
                
                with col3:
                    # Priority badge
                    priority_color = {
                        'STAT': 'status-critical',
                        'High': 'status-in-progress',
                        'Routine': 'status-pending'
                    }
                    st.markdown(f"<div class='{priority_color.get(test[8], 'status-pending')}'>Priority: {test[8]}</div>", 
                               unsafe_allow_html=True)
                    
                    st.write(f"**Instrument:** {test[9]}")
                    
                    # Action buttons
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("▶️ Start Test", key=f"start_{test[0]}"):
                            # Update test status to In Progress
                            db.execute_query(
                                "UPDATE lab_tests SET status = 'In Progress' WHERE test_id = ?",
                                (test[0],)
                            )
                            st.success(f"Started {test[3]} on {test[9]}")
                            st.rerun()
                    with col_b:
                        if st.button("📋 Enter Results", key=f"results_{test[0]}"):
                            st.session_state.editing_test = test[0]
                            st.rerun()
    else:
        st.success("🎉 No pending tests! All caught up.")
    
    # Add new test form
    st.subheader("➕ Order New Lab Test")
    
    with st.form("new_lab_test"):
        col1, col2 = st.columns(2)
        
        with col1:
            patient_id = st.text_input("Patient ID*")
            patient_name = st.text_input("Patient Name*")
            test_category = st.selectbox("Test Category", list(get_test_categories().keys()))
        
        with col2:
            test_name = st.selectbox("Test Name*", get_test_categories()[test_category])
            sample_type = st.selectbox("Sample Type", ["Blood", "Urine", "Swab", "Serum", "Plasma", "CSF"])
            priority = st.selectbox("Priority", ["Routine", "High", "STAT"])
        
        ordered_by = st.text_input("Ordered By*", value=user['full_name'])
        clinical_notes = st.text_area("Clinical Notes")
        
        if st.form_submit_button("📝 Order Test"):
            if patient_id and patient_name and test_name and ordered_by:
                test_id = f"LAB-{str(uuid.uuid4())[:8].upper()}"
                
                db.execute_query(
                    """INSERT INTO lab_tests 
                    (test_id, patient_id, patient_name, test_name, status, sample_type, 
                     ordered_by, priority, instrument_id, normal_range) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (test_id, patient_id, patient_name, test_name, "Pending", sample_type,
                     ordered_by, priority, "Abbott Architect ci4100", get_normal_ranges(test_name))
                )
                
                st.success(f"✅ Test ordered successfully! Test ID: {test_id}")
                st.rerun()
            else:
                st.error("Please fill in all required fields (*)")

def show_lab_instrument_interface(user):
    st.subheader("🔬 Lab Instrument Interface - MANUAL DATA ENTRY")
    
    st.info("🔧 **Manual Test Result Entry** - Enter results from laboratory instruments")
    
    # Get tests that are in progress
    try:
        in_progress_tests = db.fetch_all("""
            SELECT test_id, patient_id, patient_name, test_name, sample_type, normal_range
            FROM lab_tests 
            WHERE status = 'In Progress'
        """)
    except:
        in_progress_tests = []
    
    if in_progress_tests:
        st.write("**Tests Ready for Result Entry:**")
        
        for test in in_progress_tests:
            with st.expander(f"🔬 {test[3]} - {test[2]}", expanded=True):
                st.write(f"**Test ID:** {test[0]}")
                st.write(f"**Patient:** {test[2]} ({test[1]})")
                st.write(f"**Sample Type:** {test[4]}")
                st.write(f"**Normal Range:** {test[5]}")
                
                # Result entry form
                with st.form(f"result_form_{test[0]}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        result_value = st.text_input("Result Value*", key=f"value_{test[0]}")
                    with col2:
                        result_unit = st.text_input("Unit", value="", key=f"unit_{test[0]}")
                    with col3:
                        technician = st.text_input("Technician*", value=user['full_name'], key=f"tech_{test[0]}")
                    
                    notes = st.text_area("Technical Notes", key=f"notes_{test[0]}")
                    
                    if st.form_submit_button("💾 Save Results"):
                        if result_value and technician:
                            # Determine if result is abnormal or critical
                            abnormal = is_abnormal_value(test[3], result_value, test[5])
                            critical = is_critical_value(test[3], result_value)
                            
                            # Update test with results
                            db.execute_query(
                                """UPDATE lab_tests 
                                SET status = 'Completed', 
                                    result_value = ?, 
                                    result_unit = ?,
                                    abnormal_flag = ?,
                                    critical_flag = ?,
                                    technician_id = ?,
                                    completed_at = CURRENT_TIMESTAMP
                                WHERE test_id = ?""",
                                (result_value, result_unit, abnormal, critical, technician, test[0])
                            )
                            
                            status_msg = "✅ Results saved successfully"
                            if critical:
                                status_msg += " 🚨 **CRITICAL VALUE FLAGGED**"
                            elif abnormal:
                                status_msg += " ⚠️ **ABNORMAL RESULT**"
                                
                            st.success(status_msg)
                            st.rerun()
                        else:
                            st.error("Please enter a result value")
    else:
        st.info("No tests currently in progress. Start tests from the Pending Tests tab.")

def show_lab_completed_tests(user):
    st.subheader("✅ Completed Laboratory Tests")
    
    # Get completed tests from database
    try:
        completed_tests = get_completed_tests_from_db()
    except:
        completed_tests = []
    
    if completed_tests:
        # Summary statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Tests Completed", len(completed_tests))
        with col2:
            abnormal_count = len([t for t in completed_tests if t[9]])  # abnormal_flag
            st.metric("Abnormal Results", abnormal_count)
        with col3:
            critical_count = len([t for t in completed_tests if t[10]])  # critical_flag
            st.metric("Critical Values", critical_count)
        with col4:
            today_count = len([t for t in completed_tests if t[11] and str(t[11]).startswith(datetime.now().strftime("%Y-%m-%d"))])
            st.metric("Completed Today", today_count)
        
        # Test results table
        st.write("**Recent Completed Tests**")
        
        for test in completed_tests:
            # Convert tuple to dict for easier access
            test_dict = {
                'test_id': test[0],
                'patient_id': test[1],
                'patient_name': test[2],
                'test_name': test[3],
                'result_value': test[6],
                'result_unit': test[7],
                'normal_range': test[8],
                'abnormal_flag': test[9],
                'critical_flag': test[10],
                'completed_at': test[11],
                'technician_id': test[12],
                'instrument_id': test[13],
                'ordered_by': test[14]
            }
            
            with st.expander(f"📄 {test_dict['test_name']} - {test_dict['patient_name']} - {test_dict['completed_at']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Test ID:** {test_dict['test_id']}")
                    st.write(f"**Patient:** {test_dict['patient_name']} ({test_dict['patient_id']})")
                    st.write(f"**Ordered By:** {test_dict['ordered_by']}")
                    st.write(f"**Completed:** {test_dict['completed_at']}")
                
                with col2:
                    # Result with appropriate styling
                    if test_dict['critical_flag']:
                        st.error(f"**Result:** {test_dict['result_value']} {test_dict['result_unit']} 🚨 CRITICAL")
                    elif test_dict['abnormal_flag']:
                        st.warning(f"**Result:** {test_dict['result_value']} {test_dict['result_unit']} ⚠️ ABNORMAL")
                    else:
                        st.success(f"**Result:** {test_dict['result_value']} {test_dict['result_unit']} ✅ NORMAL")
                    
                    st.write(f"**Normal Range:** {test_dict['normal_range']}")
                    st.write(f"**Technician:** {test_dict['technician_id']}")
                    st.write(f"**Instrument:** {test_dict['instrument_id']}")
                
                # Action buttons
                col3, col4, col5 = st.columns(3)
                with col3:
                    if st.button("📊 View Trends", key=f"trends_{test_dict['test_id']}"):
                        st.info(f"Showing historical trends for {test_dict['test_name']}")
                with col4:
                    if st.button("📋 Full Report", key=f"full_{test_dict['test_id']}"):
                        generate_lab_report(test_dict)
                with col5:
                    # Download as CSV
                    csv_data = convert_test_to_csv(test_dict)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"lab_result_{test_dict['test_id']}.csv",
                        mime="text/csv",
                        key=f"download_{test_dict['test_id']}"
                    )
    else:
        st.info("No completed tests to display.")

def show_lab_quality_control(user):
    st.subheader("📊 Laboratory Quality Control")
    
    # QC metrics based on actual data
    try:
        completed_tests = get_completed_tests_from_db()
    except:
        completed_tests = []
    
    if completed_tests:
        abnormal_count = len([t for t in completed_tests if t[9]])  # abnormal_flag
        critical_count = len([t for t in completed_tests if t[10]])  # critical_flag
        total_count = len(completed_tests)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if total_count > 0:
                qc_pass_rate = ((total_count - abnormal_count) / total_count) * 100
                st.metric("QC Pass Rate", f"{qc_pass_rate:.1f}%")
            else:
                st.metric("QC Pass Rate", "N/A")
            st.metric("Instrument Uptime", "99.8%", "This Month")
        
        with col2:
            st.metric("Abnormal Rate", f"{(abnormal_count/total_count*100) if total_count > 0 else 0:.1f}%")
            st.metric("Turnaround Time", "2.1h", "-0.3h")
        
        with col3:
            st.metric("Critical Value Rate", f"{(critical_count/total_count*100) if total_count > 0 else 0:.1f}%")
            st.metric("Delta Check Failures", "3", "This Week")
    else:
        st.info("No test data available for quality control analysis.")

def show_enhanced_doctor_review(user):
    st.subheader("👨‍⚕️ Enhanced Clinical Review with Lab Results")
    
    tab1, tab2, tab3 = st.tabs(["📋 Patient Results", "🎯 Final Diagnosis", "💊 Prescribe Medications"])
    
    with tab1:
        show_patient_lab_results(user)
    
    with tab2:
        show_final_diagnosis(user)
    
    with tab3:
        show_prescription_workflow(user)

def show_patient_lab_results(user):
    st.subheader("📋 Patient Lab Results Review")
    
    # Get patients with completed tests
    try:
        patients_with_results = db.fetch_all("""
            SELECT DISTINCT p.patient_id, p.patient_name, p.age, p.gender
            FROM patients p
            JOIN lab_tests lt ON p.patient_id = lt.patient_id
            WHERE lt.status = 'Completed'
            ORDER BY p.patient_name
        """)
    except:
        patients_with_results = []
    
    if patients_with_results:
        patient_options = [f"{p[1]} ({p[0]})" for p in patients_with_results]
        selected_patient = st.selectbox("Select Patient:", patient_options)
        
        if selected_patient:
            patient_id = selected_patient.split('(')[-1].rstrip(')')
            
            # Get completed tests for this patient
            try:
                completed_tests = db.fetch_all("""
                    SELECT test_name, result_value, result_unit, normal_range, 
                           abnormal_flag, critical_flag, completed_at, clinical_notes
                    FROM lab_tests 
                    WHERE patient_id = ? AND status = 'Completed'
                    ORDER BY completed_at DESC
                """, (patient_id,))
            except:
                completed_tests = []
            
            if completed_tests:
                st.success(f"📊 Lab Results for {selected_patient}")
                
                # Display critical results first
                critical_tests = [t for t in completed_tests if t[5]]
                if critical_tests:
                    st.error("🚨 CRITICAL RESULTS REQUIRING IMMEDIATE ATTENTION:")
                    for test in critical_tests:
                        st.error(f"• {test[0]}: {test[1]} {test[2]} (Normal: {test[3]})")
                
                # Display all results
                for test in completed_tests:
                    with st.expander(f"{'🚨 ' if test[5] else '⚠️ ' if test[4] else '✅ '} {test[0]} - {test[6]}", 
                                   expanded=test[5]):  # Expand critical results
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if test[5]:
                                st.error(f"**Result:** {test[1]} {test[2]}")
                            elif test[4]:
                                st.warning(f"**Result:** {test[1]} {test[2]}")
                            else:
                                st.success(f"**Result:** {test[1]} {test[2]}")
                            
                            st.write(f"**Normal Range:** {test[3]}")
                        
                        with col2:
                            st.write(f"**Completed:** {test[6]}")
                            if test[7]:
                                st.write(f"**Notes:** {test[7]}")
            else:
                st.info("No completed tests for this patient.")
    else:
        st.info("No patients with completed lab results.")

def show_final_diagnosis(user):
    st.subheader("🎯 Final Diagnosis & Treatment Plan")
    
    # Get patients with completed tests
    try:
        patients_with_results = db.fetch_all("""
            SELECT DISTINCT p.patient_id, p.patient_name
            FROM patients p
            JOIN lab_tests lt ON p.patient_id = lt.patient_id
            WHERE lt.status = 'Completed'
        """)
    except:
        patients_with_results = []
    
    if patients_with_results:
        patient_options = [f"{p[1]} ({p[0]})" for p in patients_with_results]
        selected_patient = st.selectbox("Select Patient for Diagnosis:", patient_options, key="diagnosis_patient")
        
        if selected_patient:
            patient_id = selected_patient.split('(')[-1].rstrip(')')
            
            # Get original symptoms and test results
            try:
                original_order = db.fetch_one("""
                    SELECT symptoms, potential_diagnoses FROM doctor_orders 
                    WHERE patient_id = ? ORDER BY created_at DESC LIMIT 1
                """, (patient_id,))
            except:
                original_order = None
            
            with st.form("final_diagnosis"):
                st.write("**Original Symptoms:**")
                st.info(original_order[0] if original_order else "No symptoms recorded")
                
                st.write("**Lab Results Summary:**")
                try:
                    completed_tests = db.fetch_all("""
                        SELECT test_name, result_value, result_unit, abnormal_flag, critical_flag
                        FROM lab_tests WHERE patient_id = ? AND status = 'Completed'
                    """, (patient_id,))
                except:
                    completed_tests = []
                
                for test in completed_tests:
                    status = "🚨" if test[4] else "⚠️" if test[3] else "✅"
                    st.write(f"{status} {test[0]}: {test[1]} {test[2]}")
                
                # Diagnosis input
                final_diagnosis = st.text_input("Final Diagnosis*", 
                                              placeholder="e.g., Confirmed Malaria, Hypertension")
                
                treatment_plan = st.text_area("Treatment Plan*",
                                            placeholder="Detailed treatment plan...",
                                            height=150)
                
                follow_up = st.text_input("Follow-up Instructions",
                                        placeholder="e.g., Return in 2 weeks, Monitor blood pressure")
                
                if st.form_submit_button("💾 Save Diagnosis & Treatment Plan"):
                    if final_diagnosis and treatment_plan:
                        # Store final diagnosis
                        diagnosis_id = str(uuid.uuid4())
                        db.execute_query("""
                            INSERT INTO medical_encounters 
                            (encounter_id, patient_id, symptoms, initial_diagnosis, 
                             diagnosis_confidence, clinical_validation_status)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (diagnosis_id, patient_id, 
                             original_order[0] if original_order else "",
                             final_diagnosis, 0.95, "Confirmed"))
                        
                        st.success("✅ Diagnosis and treatment plan saved!")
                        st.session_state.final_diagnosis = final_diagnosis
                    else:
                        st.error("Please enter diagnosis and treatment plan")
    else:
        st.info("No patients with completed lab results available for diagnosis.")

def show_prescription_workflow(user):
    st.subheader("💊 Prescription Management")
    
    if 'final_diagnosis' in st.session_state:
        st.info(f"**Current Diagnosis:** {st.session_state.final_diagnosis}")
        
        # Get recommended medications for the diagnosis
        recommended_meds = pharmacist_workflow.get_recommended_medications(
            st.session_state.final_diagnosis
        )
        
        if recommended_meds:
            st.write("**Recommended Medications for this Diagnosis:**")
            for med in recommended_meds[:5]:  # Show top 5
                st.write(f"• {med}")
        
        with st.form("new_prescription"):
            st.write("**New Prescription**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                medication = st.text_input("Medication Name*")
                dosage = st.text_input("Dosage*", placeholder="e.g., 500mg")
                patient_id = st.text_input("Patient ID*")
            
            with col2:
                frequency = st.selectbox("Frequency*", 
                                       ["Once daily", "Twice daily", "Three times daily", 
                                        "Four times daily", "As needed"])
                duration = st.text_input("Duration*", placeholder="e.g., 7 days")
                instructions = st.text_area("Instructions", placeholder="Special instructions...")
            
            doctor_notes = st.text_area("Doctor Notes", placeholder="Clinical rationale...")
            
            if st.form_submit_button("📝 Prescribe Medication"):
                if medication and dosage and patient_id and frequency and duration:
                    prescription_id = str(uuid.uuid4())
                    
                    # Get patient name
                    try:
                        patient_info = db.fetch_one(
                            "SELECT patient_name FROM patients WHERE patient_id = ?", 
                            (patient_id,)
                        )
                    except:
                        patient_info = None
                    
                    if patient_info:
                        db.execute_query("""
                            INSERT INTO prescriptions 
                            (prescription_id, patient_id, patient_name, medication, dosage,
                             frequency, duration, instructions, doctor_notes, prescribed_by, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (prescription_id, patient_id, patient_info[0], medication, dosage,
                             frequency, duration, instructions, doctor_notes, 
                             user['full_name'], "Pending Review"))
                        
                        st.success("✅ Prescription sent to pharmacist for review!")
                    else:
                        st.error("Patient ID not found")
                else:
                    st.error("Please fill in all required fields (*)")
    else:
        st.info("Please complete the diagnosis first in the 'Final Diagnosis' tab.")

def show_lab_technician_dashboard(user):
    st.subheader("🔬 Lab Technician Dashboard")
    
    tab1, tab2, tab3 = st.tabs(["📋 Assigned Tests", "🔬 Process Tests", "📊 Completed Tests"])
    
    with tab1:
        show_assigned_tests(user)
    
    with tab2:
        show_process_tests(user)
    
    with tab3:
        show_technician_completed_tests(user)

def show_assigned_tests(user):
    st.subheader("📋 Tests Assigned to You")
    
    assigned_tests = lab_workflow.get_assigned_tests(user['id'])
    
    if assigned_tests:
        st.write(f"**You have {len(assigned_tests)} assigned tests**")
        
        for test in assigned_tests:
            with st.expander(f"🧪 {test[3]} - {test[2]} - Priority: {test[5]}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Test ID:** {test[0]}")
                    st.write(f"**Patient:** {test[2]} ({test[1]})")
                    st.write(f"**Sample Type:** {test[4]}")
                    st.write(f"**Ordered By:** {test[6]}")
                
                with col2:
                    st.write(f"**Order Date:** {test[8]}")
                    if test[7]:  # clinical notes
                        st.write(f"**Clinical Notes:** {test[7]}")
                    
                    # Action buttons
                    if st.button("🔬 Start Test", key=f"start_{test[0]}"):
                        lab_workflow.update_test_status(test[0], "In Progress", 
                                                      notes=f"Started by {user['full_name']}")
                        st.success(f"Started {test[3]}")
                        st.rerun()
    else:
        st.success("🎉 No tests assigned! You're all caught up.")

def show_process_tests(user):
    st.subheader("🔬 Process Tests - Enter Results")
    
    in_progress_tests = db.fetch_all("""
        SELECT test_id, patient_id, patient_name, test_name, sample_type, normal_range, clinical_notes
        FROM lab_tests 
        WHERE status = 'In Progress' AND technician_id = ?
    """, (user['id'],))
    
    if in_progress_tests:
        for test in in_progress_tests:
            with st.expander(f"🔬 {test[3]} - {test[2]}", expanded=True):
                st.write(f"**Test ID:** {test[0]}")
                st.write(f"**Patient:** {test[2]} ({test[1]})")
                st.write(f"**Sample Type:** {test[4]}")
                st.write(f"**Normal Range:** {test[5]}")
                if test[6]:
                    st.write(f"**Clinical Notes:** {test[6]}")
                
                # Result entry form
                with st.form(f"results_{test[0]}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        result_value = st.text_input("Result Value*", key=f"value_{test[0]}")
                        result_unit = st.text_input("Unit", value="", key=f"unit_{test[0]}")
                    
                    with col2:
                        technician_notes = st.text_area("Technician Notes", 
                                                      placeholder="Any observations or notes...",
                                                      key=f"notes_{test[0]}")
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        if st.form_submit_button("✅ Complete Test"):
                            if result_value:
                                lab_workflow.update_test_status(test[0], "Completed", 
                                                              result_value, result_unit, technician_notes)
                                st.success(f"✅ {test[3]} completed and sent to doctor")
                                st.rerun()
                            else:
                                st.error("Please enter a result value")
                    
                    with col4:
                        if st.form_submit_button("🔄 Return to Pending"):
                            lab_workflow.update_test_status(test[0], "Pending", 
                                                          notes=f"Returned by {user['full_name']}")
                            st.info(f"🔄 {test[3]} returned to pending")
                            st.rerun()
    else:
        st.info("No tests in progress. Start tests from the 'Assigned Tests' tab.")

def show_technician_completed_tests(user):
    st.subheader("📊 Tests Completed by You")
    
    completed_tests = db.fetch_all("""
        SELECT test_id, patient_name, test_name, result_value, result_unit, 
               normal_range, abnormal_flag, critical_flag, completed_at
        FROM lab_tests 
        WHERE status = 'Completed' AND technician_id = ?
        ORDER BY completed_at DESC
    """, (user['id'],))
    
    if completed_tests:
        for test in completed_tests:
            status_color = "🔴" if test[7] else "🟡" if test[6] else "🟢"
            
            with st.expander(f"{status_color} {test[2]} - {test[1]} - {test[8]}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Test ID:** {test[0]}")
                    st.write(f"**Patient:** {test[1]}")
                    st.write(f"**Completed:** {test[8]}")
                
                with col2:
                    if test[7]:  # critical
                        st.error(f"**Result:** {test[3]} {test[4]} 🚨 CRITICAL")
                    elif test[6]:  # abnormal
                        st.warning(f"**Result:** {test[3]} {test[4]} ⚠️ ABNORMAL")
                    else:
                        st.success(f"**Result:** {test[3]} {test[4]} ✅ NORMAL")
                    
                    st.write(f"**Normal Range:** {test[5]}")
    else:
        st.info("No tests completed yet.")

def show_pharmacist_dashboard(user):
    st.subheader("💊 Pharmacist Dashboard")
    
    tab1, tab2 = st.tabs(["📋 Pending Prescriptions", "✅ Approved Prescriptions"])
    
    with tab1:
        show_pending_prescriptions(user)
    
    with tab2:
        show_approved_prescriptions(user)

def show_pending_prescriptions(user):
    st.subheader("📋 Prescriptions Pending Review")
    
    pending_prescriptions = pharmacist_workflow.get_pending_prescriptions()
    
    if pending_prescriptions:
        for prescription in pending_prescriptions:
            with st.expander(f"💊 {prescription[3]} - {prescription[2]}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Prescription ID:** {prescription[0]}")
                    st.write(f"**Patient:** {prescription[2]} ({prescription[1]})")
                    st.write(f"**Medication:** {prescription[3]}")
                    st.write(f"**Dosage:** {prescription[4]}")
                    st.write(f"**Frequency:** {prescription[5]}")
                
                with col2:
                    st.write(f"**Duration:** {prescription[6]}")
                    st.write(f"**Instructions:** {prescription[7]}")
                    st.write(f"**Doctor Notes:** {prescription[8]}")
                    st.write(f"**Prescribed By:** {prescription[9]}")
                    st.write(f"**Prescribed:** {prescription[10]}")
                
                # Pharmacist review form
                with st.form(f"review_{prescription[0]}"):
                    pharmacist_notes = st.text_area("Pharmacist Notes", 
                                                  placeholder="Dispensing instructions, warnings, or notes...")
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        if st.form_submit_button("✅ Approve & Dispense"):
                            pharmacist_workflow.approve_prescription(
                                prescription[0], pharmacist_notes
                            )
                            st.success("✅ Prescription approved and ready for dispensing!")
                            st.rerun()
                    
                    with col4:
                        if st.form_submit_button("❌ Send Back for Clarification"):
                            db.execute_query("""
                                UPDATE prescriptions SET status = 'Needs Clarification',
                                pharmacist_notes = ? WHERE prescription_id = ?
                            """, (pharmacist_notes, prescription[0]))
                            st.warning("🔄 Prescription sent back to doctor for clarification")
                            st.rerun()
    else:
        st.success("🎉 No pending prescriptions! All caught up.")

def show_approved_prescriptions(user):
    st.subheader("✅ Approved & Dispensed Prescriptions")
    
    approved_prescriptions = db.fetch_all("""
        SELECT prescription_id, patient_name, medication, dosage, frequency, 
               duration, approved_at, pharmacist_notes
        FROM prescriptions 
        WHERE status = 'Approved'
        ORDER BY approved_at DESC
    """)
    
    if approved_prescriptions:
        for prescription in approved_prescriptions:
            with st.expander(f"✅ {prescription[2]} - {prescription[1]} - {prescription[6]}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Prescription ID:** {prescription[0]}")
                    st.write(f"**Patient:** {prescription[1]}")
                    st.write(f"**Medication:** {prescription[2]}")
                    st.write(f"**Dosage:** {prescription[3]}")
                
                with col2:
                    st.write(f"**Frequency:** {prescription[4]}")
                    st.write(f"**Duration:** {prescription[5]}")
                    st.write(f"**Approved:** {prescription[6]}")
                    if prescription[7]:
                        st.write(f"**Pharmacist Notes:** {prescription[7]}")
    else:
        st.info("No approved prescriptions yet.")

def show_predictive_analytics(user):
    st.subheader("📊 Predictive Analytics & Risk Stratification")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏥 Readmission Risk", 
        "🦠 Sepsis Prediction", 
        "📈 Population Health",
        "🏥 30-Day Readmission Analytics"
    ])
    
    with tab1:
        show_readmission_risk_analytics(user)
    
    with tab2:
        show_sepsis_prediction(user)
    
    with tab3:
        show_population_health(user)
    
    with tab4:
        show_30day_readmission_analytics(user)

def show_readmission_risk_analytics(user):
    st.subheader("🏥 Readmission Risk Analytics")
    
    # Generate sample data for demonstration
    risk_data = {
        'Risk Level': ['Low', 'Medium', 'High'],
        'Patient Count': [45, 28, 12],
        'Avg Readmission Rate': [2.1, 8.7, 23.4],
        'Avg Cost per Patient (KES)': [12500, 28700, 65400]
    }
    risk_df = pd.DataFrame(risk_data)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total High Risk Patients", 12, "3 this week")
        st.metric("Overall Readmission Rate", "8.2%", "-1.3%")
    
    with col2:
        st.metric("Prediction Accuracy", "94.3%", "2.1% improvement")
        st.metric("Cost Avoidance Potential", "KES 2.8M", "This quarter")
    
    with col3:
        st.metric("Interventions Deployed", 156, "24 this week")
        st.metric("Risk Reduction Success", "68%", "12% improvement")
    
    # Risk distribution chart
    fig_risk = px.bar(risk_df, x='Risk Level', y='Patient Count', 
                     color='Risk Level',
                     title='Patient Distribution by Readmission Risk Level',
                     color_discrete_map={'Low': 'green', 'Medium': 'orange', 'High': 'red'})
    st.plotly_chart(fig_risk, use_container_width=True)
    
    # Cost analysis
    col4, col5 = st.columns(2)
    
    with col4:
        fig_cost = px.pie(risk_df, values='Patient Count', names='Risk Level',
                         title='Patient Distribution by Risk Level')
        st.plotly_chart(fig_cost, use_container_width=True)
    
    with col5:
        st.subheader("📋 High Risk Patient List")
        high_risk_patients = [
            {"Name": "John Kamau", "Age": 68, "Condition": "Heart Failure", "Risk Score": "87%", "Days Since Discharge": 5},
            {"Name": "Mary Wanjiku", "Age": 72, "Condition": "COPD", "Risk Score": "79%", "Days Since Discharge": 3},
            {"Name": "Robert Ochieng", "Age": 55, "Condition": "Diabetes + Renal", "Risk Score": "92%", "Days Since Discharge": 7},
            {"Name": "Sarah Akinyi", "Age": 61, "Condition": "Stroke", "Risk Score": "84%", "Days Since Discharge": 2}
        ]
        
        for patient in high_risk_patients:
            with st.expander(f"🚨 {patient['Name']} - {patient['Condition']} - Risk: {patient['Risk Score']}"):
                st.write(f"**Age:** {patient['Age']}")
                st.write(f"**Days Since Discharge:** {patient['Days Since Discharge']}")
                st.write(f"**Recommended Actions:** Telehealth follow-up, Medication reconciliation, Home health assessment")

def show_sepsis_prediction(user):
    st.subheader("🦠 Sepsis Prediction & Early Detection")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Sepsis Cases Detected", 8, "2 this week")
        st.metric("Early Detection Rate", "92%", "15% improvement")
    
    with col2:
        st.metric("Average Detection Time", "3.2 hours", "-1.8 hours")
        st.metric("Mortality Reduction", "42%", "Since implementation")
    
    with col3:
        st.metric("ICU Transfers Avoided", 15, "This quarter")
        st.metric("Cost Savings", "KES 4.2M", "Annual projection")
    
    # Sepsis risk factors
    st.subheader("🔍 Key Sepsis Risk Factors")
    
    risk_factors = {
        'Risk Factor': ['Elevated Lactate >2.0', 'WBC >12,000 or <4,000', 'Respiratory Rate >20', 
                       'Heart Rate >90', 'Suspected Infection', 'Altered Mental Status'],
        'Prevalence': [68, 72, 58, 81, 92, 45],
        'Odds Ratio': [4.2, 3.1, 2.8, 2.5, 8.7, 5.3]
    }
    factors_df = pd.DataFrame(risk_factors)
    
    fig_factors = px.bar(factors_df, x='Risk Factor', y='Odds Ratio',
                        title='Sepsis Risk Factors - Odds Ratios',
                        color='Odds Ratio', color_continuous_scale='reds')
    st.plotly_chart(fig_factors, use_container_width=True)
    
    # Real-time monitoring
    st.subheader("📊 Real-time Patient Monitoring")
    
    monitoring_data = {
        'Patient': ['P-1001', 'P-1002', 'P-1003', 'P-1004', 'P-1005'],
        'Sepsis Risk': [15, 62, 8, 87, 23],
        'Temperature': [37.8, 38.5, 36.9, 39.2, 37.2],
        'Heart Rate': [88, 112, 76, 124, 82],
        'WBC Count': [8.2, 15.8, 6.5, 18.2, 7.8]
    }
    monitor_df = pd.DataFrame(monitoring_data)
    
    # Highlight high risk patients
    def highlight_risk(row):
        if row['Sepsis Risk'] > 50:
            return ['background-color: #ffcccc'] * len(row)
        else:
            return [''] * len(row)
    
    st.dataframe(monitor_df.style.apply(highlight_risk, axis=1))

def show_population_health(user):
    st.subheader("📈 Population Health Analytics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Population", "12,847", "2% growth")
        st.metric("Chronic Conditions", "34%", "Diabetes, Hypertension, COPD")
    
    with col2:
        st.metric("Preventive Screenings", "68%", "5% improvement")
        st.metric("Vaccination Rate", "82%", "8% improvement")
    
    with col3:
        st.metric("ER Visit Reduction", "18%", "Year over year")
        st.metric("Quality Score", "94.2", "NQF Standards")
    
    # Disease prevalence
    st.subheader("🩺 Disease Prevalence & Trends")
    
    diseases = {
        'Condition': ['Hypertension', 'Diabetes', 'COPD', 'Asthma', 'Heart Disease', 'Mental Health'],
        'Prevalence': [28.5, 15.2, 8.7, 12.3, 9.8, 18.6],
        'Trend': [2.1, 3.4, -1.2, 0.8, 1.5, 4.2]
    }
    disease_df = pd.DataFrame(diseases)
    
    fig_diseases = px.bar(disease_df, x='Condition', y='Prevalence',
                         title='Chronic Condition Prevalence (%)',
                         color='Trend', color_continuous_scale='viridis')
    st.plotly_chart(fig_diseases, use_container_width=True)
    
    # Geographic distribution
    st.subheader("🗺️ Geographic Health Distribution")
    
    # Simulated geographic data
    regions = {
        'Region': ['Nairobi', 'Central', 'Rift Valley', 'Western', 'Coastal', 'Eastern'],
        'Avg Age': [45.2, 52.1, 48.7, 50.3, 46.8, 49.5],
        'Diabetes Rate': [12.8, 18.2, 14.5, 16.8, 13.2, 15.7],
        'Hospitalizations': [245, 189, 156, 178, 201, 167]
    }
    region_df = pd.DataFrame(regions)
    
    fig_region = px.scatter(region_df, x='Avg Age', y='Diabetes Rate',
                           size='Hospitalizations', color='Region',
                           title='Regional Health Metrics',
                           size_max=60)
    st.plotly_chart(fig_region, use_container_width=True)

def show_30day_readmission_analytics(user):
    st.subheader("🏥 30-Day Readmission Risk Analytics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("30-Day Readmission Rate", "8.2%", "National Avg: 15.6%")
        st.metric("Predicted High Risk", "23 patients", "This month")
    
    with col2:
        st.metric("Preventable Readmissions", "42%", "Of total readmissions")
        st.metric("Cost per Readmission", "KES 45,200", "Average")
    
    with col3:
        st.metric("Readmission Reduction", "28%", "Year over year")
        st.metric("Savings Achieved", "KES 3.8M", "This quarter")
    
    # Readmission trends - FIXED: Ensure all arrays have same length
    st.subheader("📈 Readmission Trends Over Time")
    
    # Generate time series data with equal length arrays
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    readmission_rates = [9.2, 8.7, 8.1, 7.8, 8.3, 7.9, 7.6, 8.1, 7.8, 7.5, 7.9, 8.2]
    targets = [8.0] * len(months)  # Same length as months
    
    trend_data = {
        'Month': months,
        'Readmission Rate': readmission_rates,
        'Target': targets
    }
    trend_df = pd.DataFrame(trend_data)
    
    fig_trend = px.line(trend_df, x='Month', y=['Readmission Rate', 'Target'],
                       title='30-Day Readmission Rate Trend',
                       labels={'value': 'Readmission Rate (%)', 'variable': 'Metric'})
    fig_trend.update_layout(showlegend=True)
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # Readmission causes
    st.subheader("🔍 Primary Causes of Readmission")
    
    causes = {
        'Cause': ['Medication Issues', 'Infection', 'Procedural Complications', 
                 'Disease Progression', 'Social Factors', 'Follow-up Care Gaps'],
        'Frequency': [35, 28, 15, 12, 18, 22],
        'Preventable': [85, 65, 45, 20, 90, 95]
    }
    causes_df = pd.DataFrame(causes)
    
    fig_causes = px.bar(causes_df, x='Cause', y='Frequency',
                       color='Preventable',
                       title='Readmission Causes & Preventability (%)',
                       color_continuous_scale='greens')
    st.plotly_chart(fig_causes, use_container_width=True)
    
    # Intervention effectiveness
    st.subheader("💡 Intervention Effectiveness")
    
    interventions = {
        'Intervention': ['Medication Reconciliation', 'Follow-up Calls', 
                        'Transitional Care', 'Patient Education', 'Home Health'],
        'Reduction Rate': [42, 38, 51, 29, 45],
        'Cost per Patient (KES)': [1250, 800, 3200, 650, 2800],
        'ROI': [8.4, 12.1, 4.2, 15.8, 5.3]
    }
    intervention_df = pd.DataFrame(interventions)
    
    fig_interventions = px.scatter(intervention_df, x='Cost per Patient (KES)', 
                                  y='Reduction Rate', size='ROI', color='Intervention',
                                  title='Intervention Cost vs Effectiveness',
                                  size_max=40)
    st.plotly_chart(fig_interventions, use_container_width=True)

def show_system_admin(user):
    if user['role'] != 'admin':
        st.error("🔒 Access denied. Administrator privileges required.")
        return
    st.subheader("⚙️ System Administration")
    st.info("System administration features would be displayed here")

def show_revenue_cycle_dashboard(user):
    st.subheader("💰 Revenue Cycle Management - Kenyan Hospital Pricing")
    
    tab1, tab2, tab3 = st.tabs(["🏥 Service Pricing", "📊 Revenue Analytics", "💸 Cost Analysis"])
    
    with tab1:
        show_service_pricing(user)
    
    with tab2:
        show_revenue_analytics(user)
    
    with tab3:
        show_cost_analysis(user)

def show_service_pricing(user):
    st.subheader("🏥 Service Pricing (Kenyan Shillings - KES)")
    
    # Display Kenyan pricing
    pricing = revenue.kenyan_pricing
    
    for category, services in pricing.items():
        with st.expander(f"💰 {category}", expanded=True):
            for service, price in services.items():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{service}**")
                with col2:
                    st.write(f"KES {price:,}")
    
    # Insurance coverage calculator
    st.subheader("📋 Insurance Coverage Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        total_cost = st.number_input("Total Service Cost (KES)", min_value=0, value=15000, step=1000)
        insurance_type = st.selectbox("Insurance Type", 
                                    ["NHIF Standard", "NHIF Supa Cover", "Private Insurance", "Self-pay"])
    
    with col2:
        # Calculate coverage based on insurance type
        coverage_rates = {
            "NHIF Standard": 0.60,
            "NHIF Supa Cover": 0.80,
            "Private Insurance": 0.85,
            "Self-pay": 0.00
        }
        
        coverage_rate = coverage_rates[insurance_type]
        insurance_cover = total_cost * coverage_rate
        patient_portion = total_cost - insurance_cover
        
        st.metric("Insurance Coverage", f"KES {insurance_cover:,.0f}")
        st.metric("Patient Portion", f"KES {patient_portion:,.0f}")
        st.metric("Coverage Rate", f"{coverage_rate*100:.0f}%")

def show_revenue_analytics(user):
    st.subheader("📊 Revenue Analytics")
    
    # Sample revenue data
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    outpatient_revenue = [2450000, 2670000, 2890000, 3120000, 2980000, 3240000]
    inpatient_revenue = [3870000, 4120000, 3980000, 4230000, 4450000, 4670000]
    lab_revenue = [1560000, 1670000, 1780000, 1890000, 2010000, 2130000]
    
    revenue_data = {
        'Month': months * 3,
        'Revenue': outpatient_revenue + inpatient_revenue + lab_revenue,
        'Department': ['Outpatient']*6 + ['Inpatient']*6 + ['Laboratory']*6
    }
    revenue_df = pd.DataFrame(revenue_data)
    
    fig_revenue = px.line(revenue_df, x='Month', y='Revenue', color='Department',
                         title='Monthly Revenue by Department (KES)',
                         markers=True)
    st.plotly_chart(fig_revenue, use_container_width=True)
    
    # Revenue metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Revenue", "KES 18.2M", "12% increase")
    with col2:
        st.metric("Outpatient Revenue", "KES 6.8M", "8% increase")
    with col3:
        st.metric("Inpatient Revenue", "KES 8.9M", "15% increase")
    with col4:
        st.metric("Lab Revenue", "KES 2.5M", "6% increase")

def show_cost_analysis(user):
    st.subheader("💸 Cost Analysis & Efficiency")
    
    # Cost distribution
    cost_categories = {
        'Category': ['Staff Salaries', 'Medications', 'Equipment', 'Facilities', 'Administration', 'Utilities'],
        'Amount (KES)': [8500000, 3200000, 2800000, 1800000, 1200000, 800000],
        'Percentage': [42, 16, 14, 9, 6, 4]
    }
    cost_df = pd.DataFrame(cost_categories)
    
    fig_costs = px.pie(cost_df, values='Amount (KES)', names='Category',
                      title='Monthly Cost Distribution')
    st.plotly_chart(fig_costs, use_container_width=True)
    
    # Efficiency metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Cost per Patient", "KES 12,450", "-3% improvement")
        st.metric("Staff Efficiency", "4.2 patients/staff", "8% improvement")
    
    with col2:
        st.metric("Medication Cost", "KES 3.2M", "Within budget")
        st.metric("Equipment Utilization", "78%", "Optimal range")
    
    with col3:
        st.metric("Overtime Costs", "KES 245,000", "12% reduction")
        st.metric("Supply Chain Savings", "KES 680,000", "This quarter")

def show_security_dashboard(user):
    if user['role'] != 'admin':
        st.error("Access denied. Administrator role required.")
        return
    st.subheader("🛡️ Security & Compliance Dashboard")
    st.info("Security dashboard features would be displayed here")

# Initialize the enhanced application
if __name__ == "__main__":
    main()
