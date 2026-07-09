import re

class DomainTagger:
    """
    Tags documents with relevant domain categories based on deterministic 
    keyword matching. Used during the acquisition pipeline to map documents 
    directly into domains for model fine-tuning.
    """
    
    # Pre-defined keyword map mapping to the targeted domains.
    DOMAIN_KEYWORDS = {
        "Cyber Security": ["cyber", "information security", "infosec", "technology risk"],
        "KYC/AML": ["kyc", "know your customer", "aml", "anti-money laundering", "money laundering"],
        "IT Governance": ["it governance", "information technology governance"],
        "Outsourcing": ["outsourcing", "third party", "vendor"],
        "Fraud Risk": ["fraud", "wilful defaulter"],
        "Digital Payments": ["payment", "digital payment", "prepaid", "ppi", "cards", "wallet", "upi", "rtgs", "neft"],
        "NBFC": ["nbfc", "non-banking financial"],
        "Foreign Exchange": ["foreign exchange", "fema", "cross-border", "remittance", "forex"]
    }
    
    @classmethod
    def get_domain(cls, title: str) -> str:
        """
        Determines the single most relevant domain from a document's title 
        using deterministic keyword matching.
        
        Args:
            title (str): The document title.
            
        Returns:
            str: The matched domain category, or 'General' if no keywords match.
        """
        if not title:
            return "General"
            
        title_lower = title.lower()
        for domain, keywords in cls.DOMAIN_KEYWORDS.items():
            for kw in keywords:
                # Use word boundaries for accurate keyword targeting
                if re.search(r'\b' + re.escape(kw) + r'\b', title_lower):
                    return domain
                    
        return "General"
