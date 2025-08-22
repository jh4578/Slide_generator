"""
Query Expansion Chain for FRESCO study
Expands user queries into multiple medical domain-specific variations
"""

from typing import List, Dict, Any
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import BaseOutputParser
import json
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

logger = logging.getLogger(__name__)

class QueryExpansionOutputParser(BaseOutputParser):
    """Parser for query expansion output"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse LLM output into structured query variations
        Args:
            text: Raw LLM output
        Returns:
            Dictionary with original query and expanded variations
        """
        try:
            # Try to parse as JSON first
            if text.strip().startswith('{'):
                return json.loads(text)
            
            # Fallback: extract queries from text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            variations = []
            
            for line in lines:
                if line.startswith('-') or line.startswith('•'):
                    variations.append(line[1:].strip())
                elif line and not line.startswith('Original'):
                    variations.append(line)
            
            return {
                "original_query": "",
                "expanded_queries": variations[:5]  # Limit to 5 variations
            }
            
        except Exception as e:
            logger.error(f"Failed to parse query expansion output: {e}")
            return {
                "original_query": "",
                "expanded_queries": [text[:100]]  # Fallback to truncated text
            }

class QueryExpanderChain:
    """
    LangChain component for expanding user queries into medical domain variations
    Generates multiple query perspectives for better evidence retrieval
    """
    
    def __init__(self):
        """Initialize the query expander with medical domain prompts"""
        # Setup logging
        config.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Get OpenAI configuration
        openai_config = config.get_openai_config()
        self.llm = ChatOpenAI(
            model=openai_config['llm_model'],
            temperature=openai_config['temperature'],
            api_key=openai_config['api_key']
        )
        
        # Get search configuration
        search_config = config.get_search_config()
        self.expansion_count = search_config['expansion_count']
        
        # Create prompt template for medical query expansion
        self.prompt_template = self._create_prompt_template()
        
        # Create the LangChain
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt_template,
            output_parser=QueryExpansionOutputParser()
        )
        
        self.logger.info("QueryExpanderChain initialized successfully")
    
    def _create_prompt_template(self) -> PromptTemplate:
        """
        Create prompt template for medical query expansion
        Returns:
            PromptTemplate configured for FRESCO study context
        """
        template = """
You are a medical research assistant for the FRESCO study of fruquintinib.

Transform the user query into {expansion_count} SHORT search terms (maximum 5-6 words each).

Original Query: "{original_query}"

Generate {expansion_count} SHORT query variations in JSON format:
{{
    "original_query": "{original_query}",
    "expanded_queries": [
        "short term 1",
        "short term 2", 
        "short term 3"
    ]
}}

Rules:
- Each query must be 5-6 words maximum
- Use simple medical terms
- Include key concepts only
- No long sentences
"""
        
        return PromptTemplate(
            input_variables=["original_query", "expansion_count"],
            template=template
        )
    
    def expand_query(self, user_query: str) -> Dict[str, Any]:
        """
        Expand a user query into multiple medical variations
        Args:
            user_query: Original user query about FRESCO study
        Returns:
            Dictionary containing original query and expanded variations
        """
        self.logger.info(f"Expanding query: {user_query}")
        
        try:
            # Run the chain
            result = self.chain.invoke({
                "original_query": user_query,
                "expansion_count": self.expansion_count
            })
            
            # PRINT THE RAW LLM OUTPUT
            print(f"\n=== RAW LLM OUTPUT ===")
            print(f"Type: {type(result)}")
            print(f"Content: {result}")
            print(f"======================\n")
            
            # Ensure we have the original query
            if isinstance(result, dict):
                # Check if the result has a 'text' field (LangChain wrapped response)
                if 'text' in result and isinstance(result['text'], dict):
                    actual_result = result['text']
                    expanded_queries = actual_result.get("expanded_queries", [])
                    print(f"Found expanded_queries in result['text']: {expanded_queries}")
                else:
                    expanded_queries = result.get("expanded_queries", [])
                    print(f"Found expanded_queries directly: {expanded_queries}")
                
                result = {
                    "original_query": user_query,
                    "expanded_queries": expanded_queries
                }
            else:
                # Fallback if parsing fails
                print(f"LLM output is not dict, using fallback")
                expanded_queries = [user_query]
                result = {
                    "original_query": user_query,
                    "expanded_queries": expanded_queries
                }
            
            # Add original query to expanded list if not present
            all_queries = [user_query] + expanded_queries
            result["all_queries"] = list(dict.fromkeys(all_queries))  # Remove duplicates
            
            self.logger.info(f"Generated {len(result['all_queries'])} query variations")
            return result
            
        except Exception as e:
            self.logger.error(f"Query expansion failed: {str(e)}")
            # Return fallback result
            return {
                "original_query": user_query,
                "expanded_queries": [user_query],
                "all_queries": [user_query]
            }
    
    def get_query_variations(self, user_query: str) -> List[str]:
        """
        Convenience method to get just the list of query variations
        Args:
            user_query: Original user query
        Returns:
            List of query variations including the original
        """
        result = self.expand_query(user_query)
        return result.get("all_queries", [user_query]) 