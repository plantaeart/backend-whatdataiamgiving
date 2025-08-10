"""
MongoDB Database Configuration and Connection Manager
"""

import os
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo import IndexModel, ASCENDING, DESCENDING
import logging

logger = logging.getLogger(__name__)


# Collection names
COLLECTION_WEBSITE_ANALYSIS = "WEBSITE_TERMS_AND_CONDITION_ANALYSIS"


class MongoDB:
    """MongoDB connection manager."""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.database: Optional[Database] = None
        self._connection_string = self._get_connection_string()
        self._database_name = self._get_database_name()
    
    def _get_connection_string(self) -> str:
        """Get MongoDB connection string from environment or use default."""
        return os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    
    def _get_database_name(self) -> str:
        """Get database name from environment or use default."""
        return os.getenv("MONGODB_DATABASE", "whatdataiamgiving")
    
    def connect(self) -> bool:
        """
        Connect to MongoDB.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to MongoDB at {self._connection_string}")
            
            # Create client with timeout settings
            self.client = MongoClient(
                self._connection_string,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            
            # Test the connection
            self.client.admin.command('ping')
            
            # Get database
            self.database = self.client[self._database_name]
            
            logger.info(f"Successfully connected to MongoDB database: {self._database_name}")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client is not None:
            self.client.close()
            self.client = None
            self.database = None
            logger.info("Disconnected from MongoDB")
    
    def is_connected(self) -> bool:
        """
        Check if connected to MongoDB.
        
        Returns:
            bool: True if connected and can ping, False otherwise
        """
        if self.client is None:
            return False
        
        try:
            # Ping the database
            self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    def get_collection(self, collection_name: str) -> Optional[Collection]:
        """
        Get a collection from the database.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection object or None if not connected
        """
        if self.database is None:
            logger.error("Not connected to database")
            return None
        
        return self.database[collection_name]
    
    def get_database_info(self) -> dict:
        """
        Get database information and statistics.
        
        Returns:
            dict: Database information or empty dict if error
        """
        if self.database is None:
            return {}
        
        try:
            # Get database stats
            stats = self.database.command("dbStats")
            
            # Get collection names
            collections = self.database.list_collection_names()
            
            return {
                "database_name": self._database_name,
                "connection_string": self._connection_string.replace("mongodb://", "mongodb://***:***@") if "@" in self._connection_string else self._connection_string,
                "collections": collections,
                "stats": {
                    "collections_count": stats.get("collections", 0),
                    "objects_count": stats.get("objects", 0),
                    "avg_obj_size": stats.get("avgObjSize", 0),
                    "data_size": stats.get("dataSize", 0),
                    "storage_size": stats.get("storageSize", 0),
                    "indexes": stats.get("indexes", 0),
                    "index_size": stats.get("indexSize", 0)
                }
            }
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {}
    
    def init_collections(self) -> bool:
        """
        Initialize required collections and indexes.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self.database is None:
            logger.error("Not connected to database")
            return False
        
        try:
            # Create WEBSITE_TERMS_AND_CONDITION_ANALYSIS collection with indexes
            collection = self.database[COLLECTION_WEBSITE_ANALYSIS]
            
            # First, check if we need to drop conflicting indexes
            existing_indexes = {idx['name']: idx for idx in collection.list_indexes()}
            logger.info(f"Existing indexes: {list(existing_indexes.keys())}")
            
            # Check for conflicting privacy_score index and drop it if necessary
            if "privacy_score_desc" in existing_indexes:
                existing_key = existing_indexes["privacy_score_desc"].get("key", {})
                # If the existing index has the wrong field path, drop it
                if "privacy_score" in existing_key and "analysis.privacy_score" not in existing_key:
                    logger.info("Dropping outdated privacy_score_desc index")
                    collection.drop_index("privacy_score_desc")
            
            # Define indexes for the analysis collection based on AIAnalysisResponse + MongoDB fields
            indexes = [
                IndexModel([("url", ASCENDING)], unique=True, name="url_unique"),
                IndexModel([("analysis_id", ASCENDING)], unique=True, name="analysis_id_unique"),
                IndexModel([("created_at", DESCENDING)], name="created_at_desc"),
                IndexModel([("expires_at", ASCENDING)], name="expires_at_asc"),
                IndexModel([("analysis.privacy_score", DESCENDING)], name="privacy_score_desc"),
                IndexModel([("analysis_method", ASCENDING)], name="analysis_method_index")
            ]
            
            # Create indexes (skip existing ones that match)
            for index in indexes:
                try:
                    collection.create_indexes([index])
                except Exception as idx_error:
                    # If index already exists with correct structure, that's fine
                    if "already exists" in str(idx_error).lower() or "indexkeyspecsconflict" not in str(idx_error).lower():
                        logger.debug(f"Index {index.document.get('name', 'unnamed')} already exists or created successfully")
                    else:
                        logger.warning(f"Could not create index {index.document.get('name', 'unnamed')}: {idx_error}")
            
            logger.info(f"Successfully initialized collection '{COLLECTION_WEBSITE_ANALYSIS}' with indexes")
            
            # Log final collection info
            final_indexes = list(collection.list_indexes())
            logger.info(f"Final collection indexes: {[idx['name'] for idx in final_indexes]}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing collections: {e}")
            return False


# Global MongoDB instance
mongodb = MongoDB()


def get_mongodb() -> MongoDB:
    """Get the global MongoDB instance."""
    return mongodb


def init_mongodb() -> bool:
    """
    Initialize MongoDB connection and collections.
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Connect to MongoDB
    if not mongodb.connect():
        return False
    
    # Initialize collections and indexes
    if not mongodb.init_collections():
        logger.warning("Failed to initialize collections, but connection is established")
        # Don't return False here - connection is still working
    
    return True


def close_mongodb():
    """Close MongoDB connection."""
    mongodb.disconnect()


def get_analysis_collection():
    """
    Get the website analysis collection.
    
    Returns:
        Collection: MongoDB collection for website analysis
    """
    return mongodb.get_collection(COLLECTION_WEBSITE_ANALYSIS)
