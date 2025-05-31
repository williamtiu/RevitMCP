# RevitMCP.extension/startup.py

from pyrevit import routes
from pyrevit import script
from pyrevit import DB # For explicit Revit API access if preferred
# from Autodesk.Revit.DB import * # Alternative direct Revit API import

logger = script.get_logger()
logger.info("RevitMCP.extension startup script executing...")

try:
    # Define an API namespace. This should match the one your external server is calling.
    # The full URL will be http://<server_address>:<port>/<api_name>/<route_pattern>
    api = routes.API("revit-mcp-v1")
    logger.info("pyRevit routes API 'revit-mcp-v1' initialized in startup.py.")

    # Define the route for '/project_info' using a decorator
    @api.route('/project_info', methods=['GET'])
    def handle_get_project_info(request_data):
        """
        Handles GET requests to /revit-mcp-v1/project_info
        Returns basic information about the current Revit project.
        
        Args:
            request_data (routes.Request): Object containing request details. Not used in this simple GET.
                                           The pyRevit docs also show that you can request 'doc', 'uidoc', 'uiapp'
                                           as arguments directly if your function needs them.
                                           For example: def handle_get_project_info(doc, request_data):
        """
        route_logger = script.get_logger() # Use a logger instance for the route handler
        
        try:
            # __revit__ is a global object provided by pyRevit in the script's execution context.
            # It gives access to the Revit UIApplication object.
            # Alternatively, if 'doc' is an argument to this function, pyRevit provides it.
            
            current_uiapp = __revit__ # Or pass 'uiapp' as an argument to this handler
            if not hasattr(current_uiapp, 'ActiveUIDocument') or not current_uiapp.ActiveUIDocument:
                route_logger.error("Error accessing project info: No active UI document.")
                return routes.Response(status=503, data={"error": "No active Revit UI document found. Is a project open?"})

            doc = current_uiapp.ActiveUIDocument.Document
            if not doc:
                route_logger.error("Error accessing project info: No active document.")
                return routes.Response(status=503, data={"error": "No active Revit project document found."})
                
            project_info = doc.ProjectInformation
            if not project_info:
                route_logger.error("Error accessing project info: ProjectInformation is not available.")
                return routes.Response(status=500, data={"error": "Could not retrieve ProjectInformation from the active document."})

            data_to_return = {
                "project_name": project_info.Name,
                "project_number": project_info.Number,
                "organization_name": project_info.OrganizationName,
                "building_name": project_info.BuildingName,
                "client_name": project_info.ClientName,
                "status": project_info.Status,
                "file_path": doc.PathName,
                # Add any other project information you need
            }
            route_logger.info("Successfully retrieved project info for: {}".format(doc.PathName or "Unsaved Project"))
            return data_to_return # Automatically becomes a JSON 200 OK
            
        except AttributeError as ae:
            route_logger.error("Error accessing project info (AttributeError): {}. Is a project open and loaded?".format(ae), exc_info=True)
            return routes.Response(status=503, data={"error": "Error accessing Revit project data. A project might not be open or fully loaded.", "details": str(ae)})
        except Exception as e:
            route_logger.critical("Critical error processing /project_info: {}".format(e), exc_info=True)
            return routes.Response(status=500, data={"error": "Internal server error retrieving project info.", "details": str(e)})

    logger.info("Route /project_info for API 'revit-mcp-v1' defined in startup.py.")

    # === NEW /elements/by_category ROUTE ===
    @api.route('/elements/by_category', methods=['GET'])
    def handle_get_elements_by_category(doc, request_data):
        """
        Handles GET requests to /revit-mcp-v1/elements/by_category?category_name=OST_SomeCategory
        Returns a list of element IDs and names for the specified category.
        
        Args:
            doc (Document): The active Revit document, injected by pyRevit.
            request_data (routes.Request): Object containing request details.
        """
        route_logger = script.get_logger()
        category_name_query = request_data.params.get('category_name') # Get from query parameters

        if not category_name_query:
            route_logger.error("Missing 'category_name' query parameter.")
            return routes.Response(status=400, data={"error": "Missing 'category_name' query parameter. Use format: /elements/by_category?category_name=OST_YourCategory"})

        if not doc:
            route_logger.error("No active document available for /elements/by_category.")
            return routes.Response(status=503, data={"error": "No active Revit project document."})

        try:
            # Validate if the category_name is a valid BuiltInCategory
            # DB is Autodesk.Revit.DB, needs to be imported or available (e.g. from pyrevit import DB)
            # For safety, ensure DB is imported at the top of startup.py if not already.
            # Assuming 'from pyrevit import DB' or similar is present at the top.
            built_in_category = None
            if hasattr(DB.BuiltInCategory, category_name_query):
                built_in_category = getattr(DB.BuiltInCategory, category_name_query)
            else:
                route_logger.error("Invalid category_name: '{}'. Not a recognized BuiltInCategory.".format(category_name_query))
                # Try to list available categories for better error message - might be too verbose for here
                return routes.Response(status=400, data={"error": "Invalid category_name: '{}'. It is not a recognized BuiltInCategory.".format(category_name_query)})

            elements_collector = DB.FilteredElementCollector(doc)\
                                     .OfCategory(built_in_category)\
                                     .WhereElementIsNotElementType()\
                                     .ToElements()
            
            elements_data = []
            for el in elements_collector:
                element_name = el.Name if hasattr(el, 'Name') and el.Name else "Unnamed Element"
                elements_data.append({
                    "id": el.Id.IntegerValue,
                    "name": element_name
                })
            
            route_logger.info("Successfully retrieved {} elements for category '{}'.".format(len(elements_data), category_name_query))
            return elements_data # Returns as JSON list with 200 OK

        except AttributeError as ae: # Catch errors if DB or BuiltInCategory isn't as expected
            route_logger.error("AttributeError in /elements/by_category: {}. Is DB imported?".format(ae), exc_info=True)
            return routes.Response(status=500, data={"error": "Internal server error: Could not access Revit DB properties correctly.", "details": str(ae)})
        except Exception as e:
            route_logger.critical("Critical error processing /elements/by_category for category '{}': {}".format(category_name_query, e), exc_info=True)
            return routes.Response(status=500, data={"error": "Internal server error retrieving elements by category.", "details": str(e)})

    logger.info("Route /elements/by_category for API 'revit-mcp-v1' defined in startup.py.")

    @api.route('/select_elements_by_category', methods=['POST'])
    def handle_select_elements_by_category(doc, request_data): # ORIGINAL SIGNATURE
        logger.info("======================================================================")
        logger.info("Entering /select_elements_by_category handler")
        logger.info("ARG 'doc' - Type: {}, Value: {}".format(type(doc), doc))
        logger.info("ARG 'request_data' - Type: {}, Value: {}".format(type(request_data), request_data))
        logger.info("======================================================================")

        if not doc:
            logger.error("Critical error: 'doc' object is None or invalid.")
            return routes.Response(status=500, data={"error": "Internal server error: 'doc' object is None or invalid.", "details": "The 'doc' object was not properly provided to the handler by pyRevit."})

        if not request_data:
            logger.error("Critical error: 'request_data' object is None.")
            return routes.Response(status=500, data={"error": "Internal server error: 'request_data' object is None.", "details": "The 'request_data' object was not provided to the handler by pyRevit."})

        # If request_data is not None, try to access its properties
        try:
            logger.info("Attempting to access request_data.params: {}".format(getattr(request_data, 'params', 'N/A')))
            logger.info("Attempting to access request_data.data: {}".format(getattr(request_data, 'data', 'N/A')))
            
            payload = request_data.data # This is where you get the JSON body
            logger.info("Successfully accessed request_data.data. Type: {}, Value: {}".format(type(payload), payload))

        except Exception as e_req_access:
            logger.error("Error accessing properties of 'request_data' object: {}".format(e_req_access), exc_info=True)
            return routes.Response(status=500, data={"error": "Error accessing request_data properties", "details": str(e_req_access)})

        # ... (rest of your logic: payload processing, category validation, element selection)
        # Ensure this part is robust and uses the 'payload' variable correctly.
        # For example:
        if not payload or not isinstance(payload, dict):
            logger.error("Request body (payload) is missing or not a valid JSON object.")
            return routes.Response(status=400, data={"error": "Request body is missing or not a valid JSON object."})

        category_name_payload = payload.get('category_name')
        # ... rest of your implementation
        # ... (ensure all paths return a value)

        # Example of returning from the try block for the rest of your logic:
        try:
            # Get uidoc from __revit__ (moved here as it's part of main logic)
            current_uiapp = __revit__
            if not hasattr(current_uiapp, 'ActiveUIDocument') or not current_uiapp.ActiveUIDocument:
                logger.error("Error in /select_elements_by_category: No active UI document.")
                return routes.Response(status=503, data={"error": "No active Revit UI document found."})
            uidoc = current_uiapp.ActiveUIDocument

            # Sanity check for 'doc' consistency (optional)
            if doc.PathName != uidoc.Document.PathName and doc.Title != uidoc.Document.Title:
                logger.warning(
                    "Injected 'doc' (Title: '{}', Path: '{}') might differ from 'uidoc.Document' (Title: '{}', Path: '{}'). Using injected 'doc'.".format(
                        doc.Title, doc.PathName, uidoc.Document.Title, uidoc.Document.PathName
                    )
                )
            
            if not category_name_payload:
                logger.error("Missing 'category_name' in JSON body for /select_elements_by_category.")
                return routes.Response(status=400, data={"error": "Missing 'category_name' in JSON request body."})

            # --- Your existing logic for category validation and element selection ---
            built_in_category = None
            if hasattr(DB.BuiltInCategory, category_name_payload):
                built_in_category = getattr(DB.BuiltInCategory, category_name_payload)
            else:
                if not category_name_payload.startswith("OST_"):
                    possible_ost_category = "OST_" + category_name_payload.replace(" ", "")
                    if hasattr(DB.BuiltInCategory, possible_ost_category):
                        built_in_category = getattr(DB.BuiltInCategory, possible_ost_category)
                        logger.info("Interpreted category '{}' as '{}'.".format(category_name_payload, possible_ost_category))
                    else:
                        logger.error("Invalid category_name: '{}'. Not a recognized BuiltInCategory. Try OST_ format.".format(category_name_payload))
                        return routes.Response(status=400, data={"error": "Invalid category_name: '{}'. Not recognized.".format(category_name_payload)})
                else:
                    logger.error("Invalid category_name: '{}'. Not a recognized BuiltInCategory.".format(category_name_payload))
                    return routes.Response(status=400, data={"error": "Invalid category_name: '{}'.".format(category_name_payload)})
            
            elements_collector = DB.FilteredElementCollector(doc)\
                                    .OfCategory(built_in_category)\
                                    .WhereElementIsNotElementType()\
                                    .ToElements()
            
            element_ids_to_select = [el.Id for el in elements_collector]

            if not element_ids_to_select:
                logger.info("No elements found for category '{}' to select.".format(category_name_payload))
                return {"status": "success", "message": "No elements found for category '{}'".format(category_name_payload), "selected_count": 0, "selected_ids": []}

            uidoc.Selection.SetElementIds(element_ids_to_select)
            
            logger.info("Successfully selected {} elements for category '{}'.".format(len(element_ids_to_select), category_name_payload))
            return {"status": "success", "message": "{} elements of category '{}' selected.".format(len(element_ids_to_select), category_name_payload), "selected_count": len(element_ids_to_select), "selected_ids": [eid.IntegerValue for eid in element_ids_to_select]}

        except Exception as e_main_logic:
            # Enhanced error logging for main logic exception
            category_in_error_log = "UNKNOWN"
            if 'payload' in locals() and isinstance(payload, dict):
                category_in_error_log = payload.get('category_name', 'N/A in payload')
            elif 'category_name_payload' in locals() and category_name_payload is not None:
                 category_in_error_log = category_name_payload

            logger.critical("Critical error in main logic of /select_elements_by_category for category '{}': {}".format(category_in_error_log, e_main_logic), exc_info=True)
            return routes.Response(status=500, data={"error": "Internal server error during main logic.", "details": str(e_main_logic)})

    logger.info("Route /select_elements_by_category for API 'revit-mcp-v1' defined in startup.py.")

    # You can define more routes for the 'revit-mcp-v1' API here if needed
    # @api.route('/another_endpoint', methods=['POST'])
    # def handle_another_endpoint(request_data):
    #     # ... your logic ...
    #     return {"message": "Processed another_endpoint"}

except Exception as e:
    logger.error("Error during RevitMCP.extension startup.py execution (API/route definition): {}".format(e), exc_info=True)

logger.info("RevitMCP.extension startup script finished.") 