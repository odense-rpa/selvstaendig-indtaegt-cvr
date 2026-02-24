import pymssql


class MSSQLClient:
    """MSSQL database client with context manager support."""

    def __init__(self, host: str, user: str, password: str, database: str):
        self._connection = pymssql.connect(
            server=host,
            user=user,
            password=password,
            database=database,
            autocommit=False,
        )
        self._cursor = self._connection.cursor(as_dict=True)

    def __enter__(self):
        """Enter context, returning the object itself."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the connection gracefully upon context exit."""
        self.close()

    def close(self) -> None:
        """Close the connection gracefully."""
        if self._cursor is not None:
            self._cursor.close()
            self._cursor = None
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute a query and return the results."""
        if self._connection is None or self._cursor is None:
            raise RuntimeError("Connection is closed.")

        self._cursor.execute(query, params)
        results = self._cursor.fetchall() or []
        return results

    def hent_oplysninger(self, cpr: str) -> list:
        """Hent oplysninger for en specifik borger fra databasen."""
        query = """
            SELECT CVRnr, 
            Dato_Ajourfoering, 
            Dato_DeltagelseGyldigFra, 
            PNR, 
            Navn_FAD 
            FROM cvr_aktuelle_fad 
            WHERE PNR=%s
        """
        return self.execute_query(query, (cpr,))
