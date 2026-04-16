import saspy
import sys
from typing import Optional, Any


class SASConnection:
    """
    A wrapper class for saspy that manages SAS connections and provides
    a convenient submit method with log printing and LST output.
    """
    
    def __init__(self):
        self._sas_session: Optional[saspy.SASsession] = None
        self._connection_tested = False
    
    def _test_connection(self) -> bool:
        """
        Test if a SAS connection already exists and is active.
        
        Returns:
            bool: True if connection exists and is active, False otherwise
        """
        if self._sas_session is None:
            return False
        
        try:
            # Test the connection by submitting a simple statement            
            return  self._sas_session.SASpid is not None 
        except Exception:
            return False
    
    def _start_connection(self) -> bool:
        """
        Start a new SAS connection.

        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:

            if not self._test_connection():
               self._sas_session = saspy.SASsession(results="html")
            return self._test_connection()
        except Exception as e:
            print(f"Error starting SAS connection: {e}", file=sys.stderr)
            return False
    
    
    def submit(self, code: str) -> Optional[Any]:
        """
        Submit SAS code and return the LST output while printing the log.
        
        Args:
            code (str): SAS code to submit
            
        Returns:
            Optional[Any]: LST output object, or None if submission failed
        """
        if not self._start_connection():
            print("Cannot submit code: No SAS connection available.", file=sys.stderr)
            return None
        
        if not isinstance(code, str):
            print("Error: Code must be a string.", file=sys.stderr)
            return None
        
        if not code.strip():
            print("Warning: Empty code submitted.", file=sys.stderr)
            return None
        
        try:
            # Submit the code to SAS
            result = self._sas_session.submit(code)
            
            if result is None:
                print("Error: No result returned from SAS submission.", file=sys.stderr)
                return None
            
            # Print the log to console
            if 'LOG' in result:
                print("=== SAS LOG ===")
                print(result['LOG'])
                print("=== END LOG ===")
            else:
                print("Warning: No LOG found in result.")
            
            # Return the LST output
            if 'LST' in result:
                return result['LST']
            else:
                print("Note: No LST output generated.")
                return None
                
        except Exception as e:
            print(f"Error submitting SAS code: {e}", file=sys.stderr)
            return None
    
    def close(self):
        """Close the SAS connection."""
        if self._sas_session is not None:
            try:
                self._sas_session.endsas()
                print("SAS connection closed.")
            except Exception as e:
                print(f"Error closing SAS connection: {e}", file=sys.stderr)
            finally:
                self._sas_session = None
                self._connection_tested = False


# Create a global instance for easy access
_sas_conn = SASConnection()

# Expose the submit method at module level for convenience
def submit(code: str) -> Optional[Any]:
    """
    Submit SAS code and return the LST output while printing the log.
    
    This is a convenience function that uses a global SAS connection instance.
    
    Args:
        code (str): SAS code to submit
        
    Returns:
        Optional[Any]: LST output object, or None if submission failed
    """
    return _sas_conn.submit(code)


def close_connection():
    """Close the global SAS connection."""
    _sas_conn.close()


def get_connection() -> SASConnection:
    """
    Get the global SAS connection instance.
    
    Returns:
        SASConnection: The global connection instance
    """
    return _sas_conn


# Auto-initialize connection when module is imported
if __name__ != "__main__":
    # Only auto-initialize if not running as main script
    _sas_conn._start_connection()
