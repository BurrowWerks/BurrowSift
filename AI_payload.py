
def build_AI_prompt_payload(structured_dict_json: str)-> str:
    prompt: str = f"""
Analyze the supplied document and classify it for filing purposes.

Document:
{structured_dict_json}

Return ONLY a single JSON object containing exactly these keys:
'category', 'summary', 'subcategory', and 'tags'.

Classification rules:
- Classify the document according to its primary document type and intended purpose.
- Do not classify it only by topics, skills, industries, products, or subjects mentioned inside the document.
- Prefer the document's function over its subject matter.
- A resume that mentions education, programming, or research is still an employment resume.
- An invoice for computer equipment is still a finance invoice, not a technology document.
- A programming textbook is education or reference material, not an employment document.
- The category must be selected from the approved category values defined by the schema.
- The subcategory must be selected from the approved subcategory values defined by the schema.
- Do not invent new categories or subcategories.
- If the document does not clearly fit an approved classification, use the approved fallback classification.

Output requirements:
- 'category': the approved top-level filing category.
- 'subcategory': the approved filing subcategory that best matches the document's type and purpose.
- 'summary': a concise factual summary of the document's main purpose and key information.
- 'tags': a short list of meaningful topic labels that describe the document's content. Tags may describe subjects that are not part of the filing category.

Do not reproduce the supplied metadata or full document content.
Do not include explanations, commentary, markdown, or text outside the JSON object.
Ensure the response conforms exactly to the supplied JSON schema.
    """

    return prompt

def build_AI_config_parameters() -> dict[str, str|int]:
    ai_config: dict[str, str|int] = {
        "ai_model": "gemma4-12b-256k-test",
        "model_num_ctx": 262144,
        "max_prompt_tokens": 220000
    }
    return ai_config

def build_AI_payload_category_summary(ai_model: str, prompt: str, model_num_ctx: int,) -> dict[str, str|dict[str, str|dict[str, dict[str, str|list[str]]|dict[str, str]|dict[str, str|dict[str, str]]] | list[str] | bool | list[dict[str, dict[str, dict[str, str]|dict[str, list[str]]|dict[str, str|dict[str, str]]] | list[str]]]] | bool | dict[str, int]]:
    payload_category_summary: dict[str, str | dict[str, str | dict[str, dict[str, str | list[str]] | dict[str, str] | dict[str, str | dict[str, str]]] | list[str] | bool | list[dict[str, dict[str, dict[str, str] | dict[str, list[str]] | dict[str, str | dict[str, str]]] | list[str]]]] | bool | dict[str, int]] = {
    "model": ai_model,
        "prompt": prompt,
        "format": {
        "type": "object",
    
        "properties": {
            "category": {
                "type": "string",
                "enum": [
                    "Employment",
                    "Finance",
                    "Business",
                    "Technology",
                    "Education",
                    "Legal",
                    "Government",
                    "Health",
                    "Property",
                    "Insurance",
                    "Personal",
                    "Reference",
                    "Entertainment",
                    "Other"
                ]
            },
    
            "summary": {
                "type": "string"
            },
    
            "subcategory": {
                "type": "string"
            },
    
            "tags": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
    
        "required": [
            "category",
            "summary",
            "subcategory",
            "tags"
        ],
    
        "additionalProperties": False,
    
        "oneOf": [
            {
                "properties": {
                    "category": {
                        "const": "Employment"
                    },
                    "subcategory": {
                        "enum": [
                            "Resumes",
                            "Cover Letters",
                            "Job Applications",
                            "Employment Contracts",
                            "Payslips",
                            "Performance & HR",
                            "Compliance",
                            "Job Advertisements",
                            "Payroll"
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]
            },
    
            {
               "properties": {
                   "category": {
                       "const": "Finance"
                   },
                   "subcategory": {
                       "enum":[
                           "Banking",
                           "Tax",
                           "Invoices",
                           "Receipts",
                           "Statements",
                           "Budgets",
                           "Investments"
                       ]
                   },
                   "summary": {
                       "type": "string"
                   },
                   "tags": {
                       "type": "array",
                       "items": {
                           "type": "string"
                       }
                   }
               }, 
               "required": [
                   "category",
                   "subcategory",
                   "summary",
                   "tags"
               ]
            },
    
            {
                "properties": {
                    "category": {
                        "const": "Business"
                    },
                    "subcategory": {
                        "enum":[
                            "Operations",
                            "Projects",
                            "Reports",
                            "Policies",
                            "Procedures",
                            "Proposals",
                            "Contracts",
                            "Research"
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]
            },
    
            {
                "properties": {
                    "category": {
                        "const": "Technology"
                    },
                    "subcategory": {
                        "enum":[
                            "Programming",
                            "Documentation",
                            "Systems",
                            "Infrastructure",
                            "Security",
                            "AI"
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]
            },
    
            {
                "properties": {
                    "category": {
                        "const": "Education"
                    },
                    "subcategory": {
                        "enum": [
                            "Reference Material",
                            "Courses",
                            "Assignments",
                            "Notes",
                            "Research",
                            "Qualifications",
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]
            },
    
            {
                "properties": {
                    "category": {
                        "const": "Legal"
                    },
                    "subcategory": {
                        "enum": [
                            "Agreements",
                            "Contracts",
                            "Correspondence",
                            "Court Documents",
                            "Legal Reference"
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]
            },
    
            {
                "properties": {
                    "category": {
                        "const": "Government"
                    },
                    "subcategory": {
                        "enum": [
                            "Tax",
                            "Benefits",
                            "Licences",
                            "Applications",
                            "Correspondence"
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    } 
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]
            },
    
            {
                "properties": {
                    "category": {
                        "const": "Health"
                    },
                    "subcategory":{
                        "enum": [
                            "Medical Records",
                            "Test Results",
                            "Prescriptions",
                            "Appointments",
                            "Insurance"
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]
            },
    
            {
                "properties": {
                    "category": {
                        "const": "Property"
                    },
                    "subcategory": {
                        "enum": [
                            "Housing",
                            "Utilities",
                            "Maintenance",
                            "Leasing",
                            "Ownership"
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]
            },
    
            {
                "properties": {
                    "category": {
                        "const": "Insurance"
                    },
                    "subcategory": {
                        "enum": [
                            "Policies",
                            "Claims",
                            "Correspondence"
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]
            },
    
            {
                "properties": {
                    "category": {
                        "const": "Entertainment"
                    },
                    "subcategory": {
                        "enum": [
                            "Film",
                            "Television",
                            "Music",
                            "Video Games",
                            "Art",
                            "Theatre",
                            "Books & Literature",
                            "Festivals & Events",
                            "Comics & Manga",
                            "Podcasts",
                            "Photography",
                            "Collectibles",
                            "Reviews & Criticism",
                            "Guides & Reference"
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]    
            },
    
            {
                "properties": {
                    "category": {
                        "const": "Personal"
                    },
                    "subcategory": {
                        "enum": [
                            "Identification",
                            "Correspondence",
                            "Records",
                            "Miscellaneous"
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]
            },
    
            {
                "properties": {
                    "category": {
                        "const": "Reference"
                    },
                    "subcategory": {
                        "enum":[
                            "Manuals",
                            "Guides",
                            "Books",
                            "Articles",
                            "Research"
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]
            },
    
            {
                "properties": {
                    "category": {
                        "const": "Other"
                    },
                    "subcategory": {
                        "enum": [
                            "Uncategorized"
                        ]
                    },
                    "summary": {
                        "type": "string"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "category",
                    "subcategory",
                    "summary",
                    "tags"
                ]
            }
        ]
    },
        "stream": False,
        "think": False,
        "options": {
            "num_ctx": model_num_ctx,
            },
        }

    return payload_category_summary