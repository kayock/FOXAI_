from core.library import search_documents


class LibraryAgent:
    name = "iron_library"

    def __init__(self, app):
        self.app = app

    def handle(self, text):
        query = (
            text.replace("search my library for", "")
            .replace("search library for", "")
            .replace("find documents about", "")
            .replace("find docs about", "")
            .strip()
        )

        if not query:
            query = text.strip()

        results = search_documents(query)

        self.app.input_box.delete("1.0", "end")
        self.app.show_iron_library()
        self.app.library_box.delete("1.0", "end")
        self.app.library_box.insert("end", f"IRON LIBRARY SEARCH\n\nQuery: {query}\nResults: {len(results)}\n\n")

        for path, snippet in results[:10]:
            self.app.library_box.insert("end", f"--- {path.name} ---\n{path}\n\n{snippet}\n\n")

        return "break"