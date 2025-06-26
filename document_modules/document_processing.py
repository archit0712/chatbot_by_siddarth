"""
Document Processing Module for TechConsult Inc Knowledge Chatbot

Processes documents stored on the local filesystem and indexes them in the
vector database.
"""

import os
import tempfile
from typing import Dict, List, Any, Optional
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from core.postgres_auth import UserRole
from document_modules.document_manager import DocumentManager

class DocumentProcessor:
    """Process documents and prepare them for the vector database."""
    
    def __init__(self, vector_db=None):
        """Initialize document processor.
        
        Args:
            vector_db: Vector database instance for document storage
        """
        self.vector_db = vector_db
        self.doc_manager = DocumentManager()
    
    def process_document(self, document_id: str, user_role: UserRole) -> Dict[str, Any]:
        """Process a locally stored document and add it to the vector database."""
        try:
            doc_result = self.doc_manager.get_document_content(document_id, user_role)
            if not doc_result.get("success"):
                return {"success": False, "error": doc_result.get("error")}

            doc_data = doc_result["document"]
            file_path = doc_data.get("file_path")
            if not file_path or not os.path.exists(file_path):
                return {"success": False, "error": "File not found"}

            return self.process_pdf_file(
                file_path=file_path,
                metadata={
                    "title": doc_data.get("title", "Untitled"),
                    "document_id": document_id,
                    "min_access_level": doc_data.get("min_access_level"),
                    "document_type": doc_data.get("document_type"),
                    "description": doc_data.get("description", ""),
                    "uploaded_by": doc_data.get("uploaded_by"),
                    "uploader_email": doc_data.get("uploader_email"),
                },
            )

        except Exception as e:
            logging.error(f"Error processing document: {str(e)}")
            return {"success": False, "error": f"Processing error: {str(e)}"}
    
    def process_pdf_file(self, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process a PDF file and add chunks to vector database.
        
        Args:
            file_path: Path to the PDF file
            metadata: Document metadata
            
        Returns:
            Dict with processing status
        """
        try:
            if not self.vector_db:
                return {
                    "success": False,
                    "error": "Vector database not initialized"
                }
                
            # Load and parse PDF
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            
            # Add metadata to each document
            for doc in documents:
                doc.metadata.update(metadata)
            
            # Split into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            chunks = text_splitter.split_documents(documents)
            
            # Add to vector database
            self.vector_db.add_documents(chunks)
            
            return {
                "success": True,
                "document_id": metadata.get("document_id"),
                "chunk_count": len(chunks)
            }
            
        except Exception as e:
            logging.error(f"Error processing PDF: {str(e)}")
            return {
                "success": False,
                "error": f"Processing error: {str(e)}"
            }
    
    def process_all_accessible_documents(self, user_role: UserRole) -> Dict[str, Any]:
        """Process all documents accessible to the user's role.
        
        Args:
            user_role: Current user's role
            
        Returns:
            Dict with processing status
        """
        try:
            # Get all documents accessible to the user
            accessible_docs = self.doc_manager.get_accessible_documents(user_role)
            
            if not accessible_docs:
                return {
                    "success": True,
                    "documents_processed": 0,
                    "message": "No documents found for the user's access level"
                }
            
            processed_count = 0
            failed_count = 0
            
            for doc in accessible_docs:
                result = self.process_document(doc['id'], user_role)
                if result.get("success"):
                    processed_count += 1
                else:
                    failed_count += 1
            
            return {
                "success": True,
                "documents_processed": processed_count,
                "documents_failed": failed_count,
                "total_documents": len(accessible_docs)
            }
            
        except Exception as e:
            logging.error(f"Error processing accessible documents: {str(e)}")
            return {
                "success": False,
                "error": f"Processing error: {str(e)}"
            }
