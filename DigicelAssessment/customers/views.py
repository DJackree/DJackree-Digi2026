"""No standalone HTTP views live in this app.

Customer-facing account screens use data from ``customers.models`` through other
apps' views (for example the chatbot context and customer home template).
"""
