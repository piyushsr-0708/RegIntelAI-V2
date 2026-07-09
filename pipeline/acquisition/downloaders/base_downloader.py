import logging
from abc import ABC, abstractmethod
from pathlib import Path

class BaseDownloader(ABC):
    """
    Abstract base class defining the standard interface for all dataset downloaders 
    in the RegIntel AI project.
    """
    
    def __init__(self, base_dir: Path) -> None:
        """
        Initializes the base downloader.
        
        Args:
            base_dir (Path): The root directory where datasets and logs will be stored.
        """
        self.base_dir = base_dir
        self.setup_logging()

    def setup_logging(self) -> None:
        """Sets up a basic logger for the downloader instance."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def run(self) -> None:
        """
        Main execution method for the downloader.
        Must be implemented by all subclasses.
        """
        pass
