import streamlit as st

# Crime definitions dictionary
crime_definitions = {
    "THEFT": "Unlawful taking of property with intent to permanently deprive the owner of it.",
    "ASSAULT": "Intentional causing of apprehension of harmful or offensive contact.",
    "SEX OFFENSE": "Non-consensual sexual acts or behaviors, excluding rape.",
    "BURGLARY": "Unlawful entry into a building with intent to commit a crime.",
    "MOTOR VEHICLE THEFT": "The theft or attempted theft of a motor vehicle.",
    "OFFENSE INVOLVING CHILDREN": "Criminal offenses involving the welfare of children.",
    "CRIMINAL TRESPASS": "Unlawful entry onto property without permission.",
    "ROBBERY": "Taking property from another person by force or threat.",
    "CRIMINAL SEXUAL ASSAULT": "Sexual penetration against another's will by force or threat.",
    "STALKING": "Repeatedly following, harassing, or threatening someone.",
    "HOMICIDE": "The unlawful killing of another person.",
    "KIDNAPPING": "Unlawful confinement of a person against their will.",
    "DOMESTIC VIOLENCE": "Violent or aggressive behavior within the home, typically involving a partner."
}

# Sidebar navigation
with st.sidebar:
    st.title("Navigation")
    page = st.radio("Go to", ["Dashboard", "Crime Definitions"])
    st.text("")  # Spacer for alignment

# Page content
if page == "Dashboard":
    # Existing dashboard code
    st.title("Chicago Crime Analysis")  # Add the title here
    # (Insert the rest of your dashboard code here)
elif page == "Crime Definitions":
    st.title("Crime Definitions")
    st.write("Below are definitions for the crimes included in this dashboard:")
    
    # Display each crime and its definition
    for crime, definition in crime_definitions.items():
        st.subheader(crime)
        st.write(definition)
