"""
Script to build the local Bhubaneswar geographic database (data/bhubaneswar_locations.db)
combining Overpass OSM data with verified institutional and locality aliases.
"""
import os
import sqlite3
import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_osm_db")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "bhubaneswar_locations.db")

# Overpass QL query for Bhubaneswar bounding box (20.15, 85.60 to 20.45, 86.00)
OVERPASS_QUERY = """
[out:json][timeout:35];
(
  nwr["name"]["place"~"suburb|neighbourhood|quarter|village|city"](20.15,85.60,20.45,86.00);
  nwr["name"]["amenity"~"university|college|school|hospital|clinic|bus_station|police|fire_station|marketplace|townhall|courthouse"](20.15,85.60,20.45,86.00);
  nwr["name"]["tourism"~"attraction|theme_park"](20.15,85.60,20.45,86.00);
  nwr["name"]["historic"](20.15,85.60,20.45,86.00);
  nwr["name"]["railway"~"station|halt"](20.15,85.60,20.45,86.00);
  way["name"]["highway"~"primary|secondary|tertiary|trunk"](20.15,85.60,20.45,86.00);
);
out tags center;
"""

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
]

# Curated, verified aliases for renowned Bhubaneswar institutions, renames, acronyms, localities, squares, and civic entities
VERIFIED_ALIASES = [
    # ---------------------------------------------------------
    # City & Primary Administrative HQ
    # ---------------------------------------------------------
    ("loc_bhubaneswar", "Bhubaneswar", "city", 20.2602964, 85.8394521, "Bhubaneswar Municipal Corporation", "Ward 1-67", [
        ("bhubaneswar", "canonical"),
        ("bhubneshwar", "spelling_variation"),
        ("bhubneswar", "spelling_variation"),
        ("bhubaneshwar", "spelling_variation"),
        ("bbsr", "acronym"),
        ("temple city", "nickname")
    ]),
    ("loc_bmc_hq", "Bhubaneswar Municipal Corporation (BMC HQ)", "government", 20.2603, 85.8395, "Gautam Nagar", "Ward 46", [
        ("bmc", "acronym"),
        ("bmc bhawan", "common_name"),
        ("bmc head office", "official"),
        ("bmc hq", "acronym"),
        ("bhubaneswar municipal corporation", "canonical"),
        ("bmc office", "informal")
    ]),
    ("loc_lok_seva_bhawan", "Lok Seva Bhawan (Odisha Secretariat)", "government", 20.2708, 85.8306, "Sachivalaya Marg", "Ward 45", [
        ("secretariat", "common_name"),
        ("lok seva bhawan", "official"),
        ("odisha secretariat", "official_legacy"),
        ("state secretariat", "descriptive"),
        ("sachivalaya", "vernacular")
    ]),
    ("loc_vidhan_sabha", "Odisha Legislative Assembly (Vidhan Sabha)", "government", 20.2721, 85.8335, "Unit 5", "Ward 45", [
        ("vidhan sabha", "vernacular"),
        ("legislative assembly", "official"),
        ("odisha assembly", "short_name"),
        ("assembly bhawan", "informal"),
        ("odisha legislative assembly", "canonical")
    ]),
    ("loc_bda_hq", "Bhubaneswar Development Authority (BDA HQ)", "government", 20.2872, 85.8390, "Saheed Nagar", "Ward 30", [
        ("bda", "acronym"),
        ("bda office", "common_name"),
        ("bda bhawan", "official"),
        ("bda head office", "official"),
        ("bhubaneswar development authority", "canonical")
    ]),
    ("loc_police_commissionerate", "Police Commissionerate Headquarters", "police", 20.2755, 85.8312, "Power House Square", "Ward 40", [
        ("police commissionerate", "canonical"),
        ("commissionerate police", "common_name"),
        ("police headquarters", "official"),
        ("commissionerate hq", "acronym"),
        ("bhubaneswar police commissionerate", "compound_alias")
    ]),
    ("loc_raj_bhawan", "Raj Bhawan (Governor House)", "government", 20.2780, 85.8205, "Raj Bhawan Colony", "Ward 39", [
        ("raj bhawan", "canonical"),
        ("raj bhavan", "spelling_variation"),
        ("governor house", "common_name"),
        ("governor bhawan", "informal")
    ]),
    ("loc_heads_of_dept", "Heads of Department Building (Naatala)", "government", 20.2715, 85.8320, "Unit 5", "Ward 45", [
        ("heads of department", "canonical"),
        ("naatala", "colloquial"),
        ("naabala", "colloquial"),
        ("rajiv bhawan", "building_name"),
        ("heads of dept building", "short_name")
    ]),
    ("loc_sta_odisha", "State Transport Authority (STA) Odisha", "government", 20.2880, 85.8410, "Saheed Nagar", "Ward 30", [
        ("sta odisha", "acronym"),
        ("state transport authority", "canonical"),
        ("rto hq", "informal")
    ]),
    ("loc_rto_1", "RTO 1 Bhubaneswar", "government", 20.2875, 85.8415, "Saheed Nagar", "Ward 30", [
        ("rto 1", "canonical"),
        ("rto 1 bhubaneswar", "compound_alias"),
        ("rto saheed nagar", "locality_alias")
    ]),
    ("loc_rto_2", "RTO 2 Bhubaneswar", "government", 20.2770, 85.7890, "Baramunda", "Ward 22", [
        ("rto 2", "canonical"),
        ("rto 2 bhubaneswar", "compound_alias"),
        ("rto baramunda", "locality_alias")
    ]),
    ("loc_oshb_hq", "Odisha State Housing Board (OSHB)", "government", 20.2730, 85.8350, "Sachivalaya Marg", "Ward 45", [
        ("oshb", "acronym"),
        ("housing board bhawan", "common_name"),
        ("odisha state housing board", "canonical")
    ]),
    ("loc_osdma_hq", "Odisha State Disaster Management Authority (OSDMA)", "government", 20.2725, 85.8340, "Rajiv Bhawan", "Ward 45", [
        ("osdma", "acronym"),
        ("osdma bhawan", "common_name"),
        ("odisha disaster management authority", "canonical")
    ]),
    ("loc_optcl_hq", "OPTCL / Gridco Headquarters", "government", 20.2980, 85.8230, "Bhoinagar", "Ward 15", [
        ("optcl", "acronym"),
        ("optcl bhawan", "common_name"),
        ("gridco office", "common_name"),
        ("gridco headquarters", "official")
    ]),
    ("loc_watco_hq", "WATCO Head Office", "government", 20.2850, 85.8380, "Saheed Nagar", "Ward 30", [
        ("watco", "acronym"),
        ("watco bhubaneswar", "compound_alias"),
        ("water supply office", "informal")
    ]),

    # ---------------------------------------------------------
    # Universities, Colleges & Major Educational Institutes
    # ---------------------------------------------------------
    ("loc_cv_raman_univ", "C. V. Raman Global University", "university", 20.2198, 85.7358, "Mahura / Tamando", "Ward 65", [
        ("c. v. raman global university", "canonical"),
        ("cv raman", "common_name"),
        ("c v raman", "spaced_alias"),
        ("c. v. raman", "punctuated_alias"),
        ("cvrgu", "acronym"),
        ("c v raman global university", "official"),
        ("c v raman college of engineering", "legacy_name"),
        ("cv raman university", "informal")
    ]),
    ("loc_kiit_univ", "Kalinga Institute of Industrial Technology (KIIT)", "university", 20.3533, 85.8193, "Patia", "Ward 1", [
        ("kiit", "acronym"),
        ("kiit university", "official"),
        ("kalinga institute of industrial technology", "full_name"),
        ("kiit square", "junction"),
        ("kiit bhubaneswar", "compound_alias"),
        ("kiit campus", "landmark")
    ]),
    ("loc_utkal_univ", "Utkal University", "university", 20.3013, 85.8407, "Vani Vihar", "Ward 17", [
        ("utkal university", "canonical"),
        ("utkal", "short_name"),
        ("vani vihar university", "locality_alias"),
        ("utkal campus", "landmark")
    ]),
    ("loc_iter_soa", "Institute of Technical Education and Research (ITER / SOA)", "university", 20.2520, 85.7958, "Jagamara", "Ward 23", [
        ("iter", "acronym"),
        ("iter bhubaneswar", "compound_alias"),
        ("soa", "acronym"),
        ("soa university", "official"),
        ("siksha o anusandhan", "full_name"),
        ("institute of technical education and research", "full_name"),
        ("iter college", "informal")
    ]),
    ("loc_outr_cet", "Odisha University of Technology and Research (OUTR)", "university", 20.2762, 85.7766, "Ghatikia", "Ward 22", [
        ("outr", "acronym"),
        ("cet", "legacy_acronym"),
        ("cet bhubaneswar", "legacy_compound"),
        ("college of engineering and technology", "legacy_name"),
        ("odisha university of technology and research", "official")
    ]),
    ("loc_silicon_univ", "Silicon University", "university", 20.3504665, 85.8065029, "Patia", "Ward 1", [
        ("silicon university", "canonical"),
        ("silicon", "short_name"),
        ("silicon institute", "legacy_name"),
        ("silicon institute of technology", "official_legacy"),
        ("sit bhubaneswar", "acronym"),
        ("silicon bhubaneswar", "compound_alias"),
        ("silicon tech", "informal")
    ]),
    ("loc_iit_bbsr", "IIT Bhubaneswar", "university", 20.1520, 85.6712, "Argul / Jatni", "Outer Zone", [
        ("iit bhubaneswar", "canonical"),
        ("iit", "acronym"),
        ("iit bbsr", "short_name"),
        ("indian institute of technology bhubaneswar", "full_name"),
        ("iit argul", "locality_alias")
    ]),
    ("loc_niser_bbsr", "NISER Bhubaneswar", "university", 20.1525, 85.6775, "Jatni", "Outer Zone", [
        ("niser", "acronym"),
        ("niser bhubaneswar", "canonical"),
        ("national institute of science education and research", "full_name")
    ]),
    ("loc_ximb_univ", "Xavier Institute of Management (XIMB / XIM University)", "university", 20.3087, 85.8197, "Jaydev Vihar", "Ward 15", [
        ("ximb", "acronym"),
        ("xavier university", "official"),
        ("xim university", "brand"),
        ("xavier institute of management", "canonical"),
        ("ximb square", "junction")
    ]),
    ("loc_rd_univ", "Rama Devi Women's University", "university", 20.2878, 85.8427, "Bhoinagar / Saheed Nagar", "Ward 30", [
        ("rama devi university", "official"),
        ("rama devi womens university", "spelling_variation"),
        ("rd university", "acronym"),
        ("rd womens college", "legacy_name"),
        ("rama devi", "common_name")
    ]),
    ("loc_nift_bbsr", "NIFT Bhubaneswar", "college", 20.3580, 85.8120, "Patia", "Ward 1", [
        ("nift", "acronym"),
        ("nift bhubaneswar", "canonical"),
        ("national institute of fashion technology", "full_name")
    ]),
    ("loc_iiit_bbsr", "IIIT Bhubaneswar", "university", 20.2910, 85.7570, "Gothapatna", "Ward 22", [
        ("iiit", "acronym"),
        ("iiit bhubaneswar", "canonical"),
        ("international institute of information technology", "full_name")
    ]),
    ("loc_bput_office", "BPUT City Office Bhubaneswar", "university", 20.2760, 85.7780, "Gandamunda", "Ward 22", [
        ("bput", "acronym"),
        ("bput bhubaneswar", "compound_alias"),
        ("biju patnaik university of technology", "full_name")
    ]),
    ("loc_bjb_college", "BJB Autonomous College", "college", 20.2540, 85.8380, "BJB Nagar", "Ward 47", [
        ("bjb college", "canonical"),
        ("bjb autonomous college", "official"),
        ("baxi jagabandhu bidyadhar college", "full_name")
    ]),
    ("loc_rajdhani_college", "Rajdhani College", "college", 20.2640, 85.7970, "Baramunda", "Ward 22", [
        ("rajdhani college", "canonical"),
        ("rajdhani college bhubaneswar", "compound_alias")
    ]),
    ("loc_ouat_univ", "OUAT (Odisha University of Agriculture and Technology)", "university", 20.2650, 85.8140, "Surya Nagar", "Ward 46", [
        ("ouat", "acronym"),
        ("ouat bhubaneswar", "compound_alias"),
        ("agriculture university", "descriptive")
    ]),
    ("loc_basic_science_college", "Basic Science and Humanities College (OUAT)", "college", 20.2670, 85.8150, "Surya Nagar", "Ward 46", [
        ("basic science college", "canonical"),
        ("ouat basic science", "compound_alias")
    ]),
    ("loc_sangeet_mahavidyalaya", "Utkal Sangeet Mahavidyalaya", "college", 20.2580, 85.8430, "Kalpana", "Ward 47", [
        ("utkal sangeet mahavidyalaya", "canonical"),
        ("sangeet mahavidyalaya", "short_name")
    ]),
    ("loc_cipet_bbsr", "CIPET Bhubaneswar", "college", 20.3090, 85.8500, "Mancheswar", "Ward 18", [
        ("cipet", "acronym"),
        ("cipet bhubaneswar", "canonical"),
        ("central institute of petrochemicals engineering and technology", "full_name")
    ]),

    # ---------------------------------------------------------
    # Hospitals & Medical Institutions
    # ---------------------------------------------------------
    ("loc_aiims_bbsr", "AIIMS Bhubaneswar", "hospital", 20.2312, 85.7744, "Sijua", "Ward 64", [
        ("aiims", "acronym"),
        ("aiims bhubaneswar", "official"),
        ("all india institute of medical sciences bhubaneswar", "full_name"),
        ("aiims hospital", "informal")
    ]),
    ("loc_sum_hospital", "IMS and SUM Hospital", "hospital", 20.2835, 85.7697, "Kalinga Nagar", "Ward 22", [
        ("sum hospital", "common_name"),
        ("ims and sum hospital", "official"),
        ("sum hospital bhubaneswar", "compound_alias"),
        ("ims sum", "short_name")
    ]),
    ("loc_apollo_bbsr", "Apollo Hospitals Bhubaneswar", "hospital", 20.3060, 85.8295, "Sainik School", "Ward 12", [
        ("apollo hospital", "common_name"),
        ("apollo hospital bhubaneswar", "compound_alias"),
        ("apollo", "short_name")
    ]),
    ("loc_kims_bbsr", "KIMS Hospital", "hospital", 20.3540, 85.8160, "Patia", "Ward 1", [
        ("kims", "acronym"),
        ("kims hospital", "common_name"),
        ("kalinga institute of medical sciences", "full_name")
    ]),
    ("loc_capital_hosp", "Capital Hospital", "hospital", 20.2644, 85.8286, "Unit 6", "Ward 46", [
        ("capital hospital", "canonical"),
        ("capital hospital bhubaneswar", "compound_alias")
    ]),
    ("loc_amri_hosp", "AMRI Hospitals Bhubaneswar", "hospital", 20.2552, 85.7876, "Khandagiri", "Ward 23", [
        ("amri hospital", "common_name"),
        ("amri hospital bhubaneswar", "compound_alias"),
        ("amri", "acronym")
    ]),
    ("loc_care_hosp", "Care Hospitals Bhubaneswar", "hospital", 20.3082, 85.8123, "Chandrasekharpur", "Ward 15", [
        ("care hospital", "common_name"),
        ("care hospital bhubaneswar", "compound_alias"),
        ("care hospitals", "plural_alias")
    ]),
    ("loc_sparsh_hosp", "Sparsh Hospital & Critical Care", "hospital", 20.2980, 85.8450, "Saheed Nagar", "Ward 30", [
        ("sparsh hospital", "common_name"),
        ("sparsh hospital bhubaneswar", "compound_alias")
    ]),
    ("loc_hitech_hosp", "Hi-Tech Medical College & Hospital", "hospital", 20.2985, 85.8772, "Pandara / Rasulgarh", "Ward 18", [
        ("hi-tech hospital", "canonical"),
        ("hitech hospital", "spelling_variation"),
        ("hitech medical college", "common_name"),
        ("hi tech hospital bhubaneswar", "compound_alias")
    ]),
    ("loc_kar_clinic", "Kar Clinic & Hospital", "hospital", 20.2870, 85.8420, "Kharavela Nagar", "Ward 30", [
        ("kar clinic", "canonical"),
        ("kar hospital", "common_name")
    ]),
    ("loc_blue_wheel_hosp", "Blue Wheel Hospital", "hospital", 20.3050, 85.8180, "Mancheswar", "Ward 18", [
        ("blue wheel hospital", "canonical"),
        ("blue wheel", "short_name")
    ]),
    ("loc_sunshine_hosp", "Sunshine Hospital Bhubaneswar", "hospital", 20.3020, 85.8310, "Laxmi Vihar", "Ward 15", [
        ("sunshine hospital", "canonical")
    ]),
    ("loc_utkal_hosp", "Utkal Hospital", "hospital", 20.3340, 85.8150, "Niladri Vihar", "Ward 14", [
        ("utkal hospital", "canonical"),
        ("utkal hospital bhubaneswar", "compound_alias")
    ]),
    ("loc_lvpei_hosp", "LV Prasad Eye Institute (LVPEI)", "hospital", 20.3150, 85.8120, "Patia", "Ward 1", [
        ("lv prasad eye institute", "canonical"),
        ("lvpei", "acronym"),
        ("lvpei bhubaneswar", "compound_alias")
    ]),
    ("loc_cancer_hosp", "Regional Cancer Centre (Capital Hospital)", "hospital", 20.2640, 85.8290, "Unit 6", "Ward 46", [
        ("cancer hospital bhubaneswar", "common_name"),
        ("regional cancer centre", "official")
    ]),
    ("loc_esi_hosp", "ESI Hospital Bhubaneswar", "hospital", 20.2920, 85.8480, "Jaydev Vihar", "Ward 15", [
        ("esi hospital", "canonical"),
        ("esi hospital bhubaneswar", "compound_alias")
    ]),
    ("loc_neelachal_hosp", "Neelachal Hospital", "hospital", 20.2860, 85.8410, "Master Canteen", "Ward 41", [
        ("neelachal hospital", "canonical")
    ]),
    ("loc_ayush_hosp", "Ayush Hospital", "hospital", 20.2970, 85.8650, "Acharya Vihar / Rasulgarh", "Ward 18", [
        ("ayush hospital", "canonical")
    ]),

    # ---------------------------------------------------------
    # Transport Hubs, Railway Stations & Airports
    # ---------------------------------------------------------
    ("loc_bbsr_airport", "Biju Patnaik International Airport", "transit", 20.2444, 85.8178, "Airport Area", "Ward 50", [
        ("biju patnaik international airport", "canonical"),
        ("airport", "common_name"),
        ("bhubaneswar airport", "official_alias"),
        ("bbsr airport", "acronym"),
        ("biju patnaik airport", "short_name")
    ]),
    ("loc_bbsr_railway_station", "Bhubaneswar Railway Station (Main)", "transit", 20.2662, 85.8415, "Master Canteen", "Ward 41", [
        ("bhubaneswar railway station", "canonical"),
        ("bbsr railway station", "acronym"),
        ("bhubaneswar station", "short_name"),
        ("master canteen railway station", "locality_alias")
    ]),
    ("loc_new_bbsr_station", "New Bhubaneswar Railway Station", "transit", 20.3680, 85.8250, "Patia / Barang", "Outer Zone", [
        ("new bhubaneswar railway station", "canonical"),
        ("new bhubaneswar station", "short_name")
    ]),
    ("loc_mancheswar_station", "Mancheswar Railway Station", "transit", 20.3150, 85.8620, "Mancheswar", "Ward 18", [
        ("mancheswar railway station", "canonical"),
        ("mancheswar station", "short_name")
    ]),
    ("loc_lingaraj_station", "Lingaraj Temple Road Railway Station", "transit", 20.2320, 85.8320, "Old Town", "Ward 58", [
        ("lingaraj railway station", "canonical"),
        ("lingaraj temple road station", "official")
    ]),
    ("loc_baramunda_isbt", "Baramunda ISBT (Babasaheb Bhimrao Ambedkar Bus Terminal)", "transit", 20.2785, 85.7950, "Baramunda", "Ward 22", [
        ("baramunda", "locality"),
        ("baramunda bus stand", "transit"),
        ("baramunda isbt", "official"),
        ("babasaheb bhimrao ambedkar bus terminal", "official_new"),
        ("baramunda bus terminal", "common_name")
    ]),
    ("loc_patia_bus_stand", "Patia Bus Stand", "transit", 20.3588, 85.8164, "Patia", "Ward 1", [
        ("patia bus stand", "canonical"),
        ("patia bus stop", "informal")
    ]),
    ("loc_master_canteen_bus_stand", "Master Canteen Bus Terminal", "transit", 20.2660, 85.8410, "Master Canteen", "Ward 41", [
        ("master canteen bus stand", "canonical"),
        ("master canteen bus stop", "informal")
    ]),

    # ---------------------------------------------------------
    # Landmarks, Temples, Parks, Museums & Public Spaces
    # ---------------------------------------------------------
    ("loc_lingaraj_temple", "Lingaraj Temple", "landmark", 20.2382, 85.8338, "Old Town", "Ward 58", [
        ("lingaraj temple", "canonical"),
        ("lingaraj", "short_name"),
        ("old town", "locality"),
        ("old town bhubaneswar", "compound_alias")
    ]),
    ("loc_rajarani_temple", "Rajarani Temple", "landmark", 20.2447, 85.8436, "Rajarani Colony", "Ward 57", [
        ("rajarani temple", "canonical"),
        ("rajarani", "short_name")
    ]),
    ("loc_mukteshwar_temple", "Mukteshwar Temple", "landmark", 20.2432, 85.8398, "Old Town", "Ward 57", [
        ("mukteshwar temple", "canonical"),
        ("mukteswar temple", "spelling_variation"),
        ("mukteswar", "short_name")
    ]),
    ("loc_ananta_vasudeva", "Ananta Vasudeva Temple", "landmark", 20.2395, 85.8345, "Old Town", "Ward 58", [
        ("ananta vasudeva temple", "canonical"),
        ("ananta vasudeva", "short_name")
    ]),
    ("loc_iskcon_temple", "ISKCON Temple Bhubaneswar", "landmark", 20.2975, 85.8118, "Nayapalli", "Ward 15", [
        ("iskcon temple", "canonical"),
        ("iskcon", "acronym"),
        ("iskcon bhubaneswar", "compound_alias")
    ]),
    ("loc_ram_mandir", "Ram Mandir Bhubaneswar", "landmark", 20.2830, 85.8410, "Kharavela Nagar", "Ward 30", [
        ("ram mandir", "canonical"),
        ("ram mandir bhubaneswar", "compound_alias"),
        ("ram mandir square", "junction")
    ]),
    ("loc_khandagiri_caves", "Khandagiri & Udayagiri Caves", "landmark", 20.2570, 85.7865, "Khandagiri", "Ward 23", [
        ("khandagiri", "canonical"),
        ("khandagiri caves", "landmark"),
        ("udayagiri caves", "landmark"),
        ("khandagiri udayagiri", "compound_alias")
    ]),
    ("loc_dhauli_stupa", "Dhauli Shanti Stupa (Peace Pagoda)", "landmark", 20.1920, 85.8394, "Dhauli", "Outer Zone", [
        ("dhauli", "canonical"),
        ("shanti stupa", "common_name"),
        ("dhauli peace pagoda", "official"),
        ("dhauli hill", "landmark")
    ]),
    ("loc_nandankanan_zoo", "Nandankanan Zoological Park", "landmark", 20.3950, 85.8250, "Nandankanan", "Outer Zone", [
        ("nandankanan", "canonical"),
        ("nandankanan zoo", "common_name"),
        ("nandankanan zoological park", "official")
    ]),
    ("loc_kalinga_stadium", "Kalinga Stadium", "landmark", 20.3045, 85.8242, "Nayapalli", "Ward 15", [
        ("kalinga stadium", "canonical"),
        ("kalinga stadium square", "junction"),
        ("kalinga sports complex", "descriptive")
    ]),
    ("loc_state_museum", "Odisha State Museum", "landmark", 20.2555, 85.8425, "BJB Nagar / Kalpana", "Ward 47", [
        ("state museum", "canonical"),
        ("odisha state museum", "official"),
        ("museum kalpana", "locality_alias")
    ]),
    ("loc_tribal_museum", "Tribal Museum (Museum of Tribal Arts & Artifacts)", "landmark", 20.2740, 85.8120, "CRPF Square", "Ward 39", [
        ("tribal museum", "canonical"),
        ("museum of tribal arts", "official"),
        ("tribal museum bhubaneswar", "compound_alias")
    ]),
    ("loc_natural_history_museum", "Regional Museum of Natural History", "landmark", 20.3030, 85.8310, "Acharya Vihar", "Ward 15", [
        ("natural history museum", "canonical"),
        ("regional museum of natural history", "official")
    ]),
    ("loc_planetarium", "Pathani Samanta Planetarium", "landmark", 20.3018, 85.8315, "Acharya Vihar", "Ward 15", [
        ("planetarium", "canonical"),
        ("pathani samanta planetarium", "official"),
        ("planetarium bhubaneswar", "compound_alias")
    ]),
    ("loc_science_centre", "Regional Science Centre", "landmark", 20.3025, 85.8305, "Acharya Vihar", "Ward 15", [
        ("science centre", "canonical"),
        ("regional science centre bhubaneswar", "official")
    ]),
    ("loc_ekamra_kanan", "Ekamra Kanan Botanical Park", "park", 20.3055, 85.8085, "IRC Village", "Ward 15", [
        ("ekamra kanan", "canonical"),
        ("ekamra kanan park", "common_name"),
        ("cactus garden bhubaneswar", "landmark")
    ]),
    ("loc_ig_park", "Indira Gandhi Park (IG Park)", "park", 20.2685, 85.8322, "Unit 2", "Ward 45", [
        ("ig park", "canonical"),
        ("indira gandhi park", "official"),
        ("ig park bhubaneswar", "compound_alias")
    ]),
    ("loc_forest_park", "Biju Patnaik Park (Forest Park)", "park", 20.2590, 85.8230, "Unit 6", "Ward 46", [
        ("forest park", "canonical"),
        ("biju patnaik park", "official"),
        ("forest park bhubaneswar", "compound_alias")
    ]),
    ("loc_mg_park", "Mahatma Gandhi Park", "park", 20.2980, 85.8150, "Jaydev Vihar", "Ward 15", [
        ("mahatma gandhi park", "canonical"),
        ("mg park", "acronym")
    ]),
    ("loc_jayadev_vatika", "Jayadev Vatika", "park", 20.2530, 85.7820, "Khandagiri", "Ward 23", [
        ("jayadev vatika", "canonical"),
        ("jaydev vatika", "spelling_variation")
    ]),
    ("loc_buddha_park", "Buddha Jayanti Park", "park", 20.3320, 85.8130, "Niladri Vihar", "Ward 14", [
        ("buddha jayanti park", "canonical"),
        ("buddha park", "short_name")
    ]),
    ("loc_unit_1_market", "Unit 1 Daily Market", "marketplace", 20.2650, 85.8340, "Unit 1", "Ward 41", [
        ("unit 1 market", "canonical"),
        ("unit 1", "locality"),
        ("unit 1 haat", "local_name")
    ]),
    ("loc_unit_2_market", "Unit 2 Market Building", "marketplace", 20.2668, 85.8361, "Unit 2", "Ward 41", [
        ("market building", "canonical"),
        ("unit 2 market", "common_name"),
        ("unit 2 market building", "official")
    ]),
    ("loc_saheed_nagar_market", "Saheed Nagar Market", "marketplace", 20.2880, 85.8440, "Saheed Nagar", "Ward 30", [
        ("saheed nagar market", "canonical"),
        ("sahid nagar market", "spelling_variation")
    ]),
    ("loc_indradhanu_market", "Indradhanu Market", "marketplace", 20.2990, 85.8120, "IRC Village", "Ward 15", [
        ("indradhanu market", "canonical"),
        ("irc village market", "locality_alias")
    ]),

    # ---------------------------------------------------------
    # Major Roads, Highways & Corridors
    # ---------------------------------------------------------
    ("loc_janpath_road", "Janpath Road", "highway", 20.2800, 85.8400, "Vani Vihar to Sishu Bhawan", "Multiple Wards", [
        ("janpath", "canonical"),
        ("janpath road", "common_name")
    ]),
    ("loc_cuttack_puri_road", "Cuttack-Puri Road", "highway", 20.2750, 85.8550, "Master Canteen to Rasulgarh", "Multiple Wards", [
        ("cuttack road", "canonical"),
        ("cuttack puri road", "common_name"),
        ("cuttack puri highway", "informal")
    ]),
    ("loc_nandankanan_road", "Nandankanan Road", "highway", 20.3200, 85.8200, "Jaydev Vihar to Nandankanan", "Multiple Wards", [
        ("nandankanan road", "canonical"),
        ("nandan kanan road", "spelling_variation"),
        ("jaydev vihar nandankanan road", "compound_alias")
    ]),
    ("loc_lewis_road", "Lewis Road", "highway", 20.2450, 85.8400, "Kalpana to Old Town", "Ward 57", [
        ("lewis road", "canonical"),
        ("lewis road bhubaneswar", "compound_alias")
    ]),
    ("loc_nh_16", "NH 16 (National Highway 16)", "highway", 20.2921, 85.8198, "Khandagiri to Rasulgarh Bypass", "Multiple Wards", [
        ("nh 16", "canonical"),
        ("nh16", "short_name"),
        ("national highway 16", "official"),
        ("bhubaneswar bypass", "descriptive")
    ]),
    ("loc_chandaka_road", "Khandagiri - Chandaka Road", "highway", 20.2650, 85.7750, "Khandagiri", "Ward 23", [
        ("chandaka road", "canonical"),
        ("khandagiri chandaka road", "compound_alias")
    ]),
    ("loc_infocity_road", "Patia - Infocity Road", "highway", 20.3550, 85.8120, "Patia", "Ward 1", [
        ("infocity road", "canonical"),
        ("patia station road", "informal")
    ]),
    ("loc_sachivalaya_marg", "Sachivalaya Marg", "highway", 20.2850, 85.8320, "AG Square to Jaydev Vihar", "Multiple Wards", [
        ("sachivalaya marg", "canonical"),
        ("secretariat road", "common_name")
    ]),
    ("loc_ekamra_marg", "Ekamra Marg", "highway", 20.2600, 85.8300, "Forest Park to Capital Hospital", "Ward 46", [
        ("ekamra marg", "canonical")
    ]),
    ("loc_airport_road", "Airport Road", "highway", 20.2520, 85.8220, "Capital Hospital to Airport", "Ward 50", [
        ("airport road", "canonical")
    ]),
    ("loc_puri_bypass", "Puri Bypass Road", "highway", 20.2300, 85.8500, "Rasulgarh to Samantarapur", "Outer Zone", [
        ("puri bypass", "canonical"),
        ("puri bypass road", "common_name")
    ]),
    ("loc_ghatikia_road", "Ghatikia Main Road", "highway", 20.2714, 85.7700, "Ghatikia", "Ward 22", [
        ("ghatikia road", "canonical"),
        ("ghatikia main road", "official")
    ]),
    ("loc_niladri_vihar_road", "Niladrivihar Main Road", "highway", 20.3266, 85.8152, "Niladri Vihar", "Ward 14", [
        ("niladri vihar road", "canonical"),
        ("niladrivihar main road", "official")
    ]),
    ("loc_pokhariput_road", "Pokhariput Flyover / Road", "highway", 20.2349, 85.8140, "Pokhariput", "Ward 62", [
        ("pokhariput road", "canonical"),
        ("pokhariput flyover", "landmark")
    ]),
    ("loc_rajmahal_flyover", "Rajmahal Flyover", "highway", 20.2635, 85.8355, "Rajmahal Square", "Ward 41", [
        ("rajmahal flyover", "canonical")
    ]),

    # ---------------------------------------------------------
    # Major Squares, Intersections & Chhaks
    # ---------------------------------------------------------
    ("loc_jaydev_vihar", "Jaydev Vihar Square (Jaydev Vihar Chhak)", "square", 20.3015, 85.8236, "Jaydev Vihar", "Ward 15", [
        ("jaydev vihar", "canonical"),
        ("jayadev vihar", "spelling_variation"),
        ("jaydev vihar square", "junction"),
        ("jaydev vihar chhak", "local_name"),
        ("jayadev vihar square", "junction_alt"),
        ("jayadev vihar chhak", "local_name_alt")
    ]),
    ("loc_rasulgarh", "Rasulgarh Square (Rasulgarh Chhak)", "square", 20.2980, 85.8670, "Rasulgarh", "Ward 18", [
        ("rasulgarh", "canonical"),
        ("rasulgarh square", "junction"),
        ("rasulgarh chhak", "local_name")
    ]),
    ("loc_khandagiri", "Khandagiri Square (Khandagiri Chhak)", "square", 20.2570, 85.7865, "Khandagiri", "Ward 23", [
        ("khandagiri", "canonical"),
        ("khandagiri square", "junction"),
        ("khandagiri chhak", "local_name")
    ]),
    ("loc_patia", "Patia Square (Patia Chhak)", "square", 20.3588, 85.8164, "Patia", "Ward 1", [
        ("patia", "canonical"),
        ("patia square", "junction"),
        ("patia chhak", "local_name"),
        ("patia station", "transit")
    ]),
    ("loc_master_canteen", "Master Canteen Square (Master Canteen Chhak)", "square", 20.2662, 85.8415, "Kharavela Nagar", "Ward 41", [
        ("master canteen", "canonical"),
        ("master canteen square", "junction"),
        ("master canteen chhak", "local_name")
    ]),
    ("loc_ag_square", "AG Square (AG Chhak)", "square", 20.2702, 85.8300, "Unit 5 / Secretariat", "Ward 45", [
        ("ag square", "canonical"),
        ("ag chhak", "local_name"),
        ("accountant general square", "full_name"),
        ("ag office square", "informal")
    ]),
    ("loc_crpf_square", "CRPF Square (CRPF Chhak)", "square", 20.2915, 85.8055, "Nayapalli", "Ward 39", [
        ("crpf square", "canonical"),
        ("crpf chhak", "local_name"),
        ("crpf campus", "landmark")
    ]),
    ("loc_vani_vihar_square", "Vani Vihar Square (Vani Vihar Chhak)", "square", 20.2926, 85.8533, "Vani Vihar", "Ward 17", [
        ("vani vihar square", "canonical"),
        ("vani vihar chhak", "local_name"),
        ("vani vihar junction", "descriptive")
    ]),
    ("loc_kalpana_square", "Kalpana Square (Kalpana Chhak)", "square", 20.2540, 85.8430, "BJB Nagar", "Ward 47", [
        ("kalpana square", "canonical"),
        ("kalpana chhak", "local_name"),
        ("kalpana junction", "descriptive")
    ]),
    ("loc_rajmahal_square", "Rajmahal Square (Rajmahal Chhak)", "square", 20.2635, 85.8355, "Unit 1", "Ward 41", [
        ("rajmahal square", "canonical"),
        ("rajmahal chhak", "local_name")
    ]),
    ("loc_acharya_vihar_square", "Acharya Vihar Square (Acharya Vihar Chhak)", "square", 20.2980, 85.8320, "Acharya Vihar", "Ward 15", [
        ("acharya vihar square", "canonical"),
        ("acharya vihar chhak", "local_name"),
        ("acharya vihar", "locality")
    ]),
    ("loc_fire_station_square", "Fire Station Square (Fire Station Chhak)", "square", 20.2780, 85.7980, "Baramunda", "Ward 22", [
        ("fire station square", "canonical"),
        ("fire station chhak", "local_name")
    ]),
    ("loc_ravi_talkies_square", "Ravi Talkies Square (Ravi Talkies Chhak)", "square", 20.2460, 85.8410, "Old Town", "Ward 57", [
        ("ravi talkies square", "canonical"),
        ("ravi talkies chhak", "local_name"),
        ("ravi talkies", "short_name")
    ]),
    ("loc_samantarapur_square", "Samantarapur Square (Samantarapur Chhak)", "square", 20.2250, 85.8450, "Samantarapur", "Ward 59", [
        ("samantarapur square", "canonical"),
        ("samantarapur chhak", "local_name"),
        ("samantarapur", "locality")
    ]),
    ("loc_sishu_bhawan_square", "Sishu Bhawan Square (Sishu Bhawan Chhak)", "square", 20.2580, 85.8310, "Unit 1", "Ward 46", [
        ("sishu bhawan square", "canonical"),
        ("sishu bhawan chhak", "local_name"),
        ("sishu bhawan", "short_name")
    ]),
    ("loc_governor_house_square", "Governor House Square (Raj Bhawan Chhak)", "square", 20.2770, 85.8220, "Raj Bhawan", "Ward 39", [
        ("governor house square", "canonical"),
        ("raj bhawan square", "common_name"),
        ("raj bhawan chhak", "local_name")
    ]),
    ("loc_power_house_square", "Power House Square", "square", 20.2750, 85.8310, "Unit 5", "Ward 40", [
        ("power house square", "canonical"),
        ("power house chhak", "local_name")
    ]),
    ("loc_damana_square", "Damana Square (Damana Chhak)", "square", 20.3380, 85.8150, "Chandrasekharpur", "Ward 14", [
        ("damana square", "canonical"),
        ("damana chhak", "local_name"),
        ("damana", "locality")
    ]),
    ("loc_big_bazaar_square", "Patia Big Bazaar Square", "square", 20.3480, 85.8160, "Patia", "Ward 1", [
        ("patia big bazaar square", "canonical"),
        ("big bazaar chhak", "local_name")
    ]),
    ("loc_nageswar_tangi_square", "Nageswar Tangi Square", "square", 20.2410, 85.8380, "Old Town", "Ward 57", [
        ("nageswar tangi square", "canonical"),
        ("nageswar tangi", "locality")
    ]),

    # ---------------------------------------------------------
    # Key Localities, Sectors & Residential Neighborhoods
    # ---------------------------------------------------------
    ("loc_saheed_nagar", "Saheed Nagar", "locality", 20.2882, 85.8458, "Saheed Nagar", "Ward 30", [
        ("saheed nagar", "canonical"),
        ("sahid nagar", "spelling_variation")
    ]),
    ("loc_nayapalli", "Nayapalli", "locality", 20.2977, 85.8145, "Nayapalli", "Ward 15", [
        ("nayapalli", "canonical"),
        ("nayapali", "spelling_variation"),
        ("irc village", "sub_locality")
    ]),
    ("loc_cs_pur", "Chandrasekharpur", "locality", 20.3294, 85.8178, "Chandrasekharpur", "Ward 14", [
        ("chandrasekharpur", "canonical"),
        ("cs pur", "acronym"),
        ("chandrasekharpur locality", "descriptive")
    ]),
    ("loc_sailashree_vihar", "Sailashree Vihar", "locality", 20.3360, 85.8110, "Chandrasekharpur", "Ward 14", [
        ("sailashree vihar", "canonical"),
        ("sailashree", "short_name")
    ]),
    ("loc_niladri_vihar", "Niladri Vihar", "locality", 20.3266, 85.8152, "Chandrasekharpur", "Ward 14", [
        ("niladri vihar", "canonical"),
        ("niladrivihar", "spelling_variation")
    ]),
    ("loc_mancheswar", "Mancheswar Industrial Estate", "locality", 20.3069, 85.8514, "Mancheswar", "Ward 18", [
        ("mancheswar", "canonical"),
        ("mancheswar industrial estate", "official")
    ]),
    ("loc_dumduma", "Dumduma Housing Board", "locality", 20.2450, 85.7720, "Dumduma", "Ward 63", [
        ("dumduma", "canonical"),
        ("dumduma housing board", "official")
    ]),
    ("loc_sundarpada", "Sundarpada", "locality", 20.2320, 85.8157, "Sundarpada", "Ward 66", [
        ("sundarpada", "canonical")
    ]),
    ("loc_tamando", "Tamando", "locality", 20.2384, 85.7461, "Tamando", "Ward 65", [
        ("tamando", "canonical")
    ]),
    ("loc_pokhariput", "Pokhariput", "locality", 20.2349, 85.8140, "Pokhariput", "Ward 62", [
        ("pokhariput", "canonical")
    ]),
    ("loc_badagada", "Badagada Brit Colony", "locality", 20.2580, 85.8520, "Badagada", "Ward 56", [
        ("badagada", "canonical"),
        ("badagada brit colony", "official")
    ]),
    ("loc_jharpada", "Jharpada", "locality", 20.2820, 85.8600, "Jharpada", "Ward 32", [
        ("jharpada", "canonical"),
        ("jharpada jail", "landmark")
    ]),
    ("loc_ghatikia", "Ghatikia", "locality", 20.2714, 85.7700, "Ghatikia", "Ward 22", [
        ("ghatikia", "canonical")
    ]),
    ("loc_kalinga_nagar_loc", "Kalinga Nagar Locality", "locality", 20.2780, 85.7650, "Kalinga Nagar", "Ward 22", [
        ("kalinga nagar", "canonical"),
        ("kalinga nagar bhubaneswar", "compound_alias")
    ]),
    ("loc_laxmi_vihar", "Laxmi Vihar", "locality", 20.3010, 85.8350, "Sainik School / Vani Vihar", "Ward 15", [
        ("laxmi vihar", "canonical")
    ]),
    ("loc_unit_1", "Unit 1 Sector", "locality", 20.2650, 85.8330, "Unit 1", "Ward 41", [
        ("unit 1", "canonical")
    ]),
    ("loc_unit_2", "Unit 2 Sector", "locality", 20.2680, 85.8350, "Unit 2", "Ward 41", [
        ("unit 2", "canonical")
    ]),
    ("loc_unit_3", "Unit 3 Kharavela Nagar", "locality", 20.2750, 85.8420, "Kharavela Nagar", "Ward 41", [
        ("unit 3", "canonical"),
        ("kharavela nagar", "official")
    ]),
    ("loc_unit_4", "Unit 4 Bhauma Nagar", "locality", 20.2780, 85.8380, "Bhauma Nagar", "Ward 41", [
        ("unit 4", "canonical")
    ]),
    ("loc_unit_6", "Unit 6 Ganga Nagar", "locality", 20.2600, 85.8240, "Ganga Nagar", "Ward 46", [
        ("unit 6", "canonical")
    ]),
    ("loc_unit_8", "Unit 8 Delta Square", "locality", 20.2800, 85.8120, "Delta Colony", "Ward 39", [
        ("unit 8", "canonical"),
        ("delta square", "junction")
    ]),
    ("loc_unit_9", "Unit 9 Bayababa", "locality", 20.2850, 85.8480, "Saheed Nagar", "Ward 30", [
        ("unit 9", "canonical")
    ])
]


def init_db(conn):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        id TEXT PRIMARY KEY,
        canonical_name TEXT NOT NULL,
        category TEXT NOT NULL,
        sub_category TEXT,
        locality TEXT,
        ward TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        osm_id TEXT,
        source TEXT DEFAULT 'OSM'
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS location_aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id TEXT NOT NULL,
        alias_normalized TEXT NOT NULL,
        alias_type TEXT NOT NULL,
        confidence REAL DEFAULT 1.0,
        FOREIGN KEY (location_id) REFERENCES locations(id)
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_name ON locations(canonical_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alias_norm ON location_aliases(alias_normalized);")
    conn.commit()


def normalize_text(text: str) -> str:
    import re
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r'[\(\)\[\]\{\}\.,\/\\\-_:;!?"\']', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def fetch_osm_data():
    logger.info("Querying Overpass API for Bhubaneswar bounding box data...")
    for ep in OVERPASS_ENDPOINTS:
        try:
            logger.info(f"Attempting Overpass endpoint: {ep}")
            r = requests.post(ep, data={"data": OVERPASS_QUERY}, headers={"User-Agent": "CivicLensBuilder/1.0"}, timeout=35)
            if r.status_code == 200:
                data = r.json()
                elements = data.get("elements", [])
                logger.info(f"Fetched {len(elements)} raw elements from {ep}")
                return elements
            else:
                logger.warning(f"Endpoint {ep} returned HTTP {r.status_code}")
        except Exception as e:
            logger.warning(f"Error fetching from {ep}: {e}")
    logger.error("All Overpass endpoints failed. Proceeding with verified base registry.")
    return []


def populate_database():
    os.makedirs(DB_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            logger.info(f"Removed previous database file {DB_PATH}")
        except Exception as e:
            logger.warning(f"Could not remove old DB: {e}")

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    cursor = conn.cursor()

    # 1. Insert curated verified locations & aliases
    logger.info("Inserting verified institutional and locality aliases...")
    for loc_id, name, cat, lat, lon, locality, ward, aliases in VERIFIED_ALIASES:
        cursor.execute(
            "INSERT OR REPLACE INTO locations (id, canonical_name, category, locality, ward, latitude, longitude, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (loc_id, name, cat, locality, ward, lat, lon, "VERIFIED_REGISTRY")
        )
        for alias_str, a_type in aliases:
            norm_a = normalize_text(alias_str)
            if norm_a:
                cursor.execute(
                    "INSERT INTO location_aliases (location_id, alias_normalized, alias_type, confidence) VALUES (?, ?, ?, ?)",
                    (loc_id, norm_a, a_type, 1.0)
                )

    # 2. Fetch and merge OSM entities
    osm_elements = fetch_osm_data()
    inserted_osm = 0
    for el in osm_elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name or not name.strip():
            continue

        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue

        # Strict bounding box check for Bhubaneswar
        if not (20.15 <= lat <= 20.45 and 85.60 <= lon <= 86.00):
            continue

        osm_id = f"osm_{el.get('type', 'node')}_{el.get('id')}"
        cat = tags.get("amenity") or tags.get("place") or tags.get("highway") or tags.get("tourism") or tags.get("historic") or "landmark"

        # Check if already inserted via verified registry
        norm_name = normalize_text(name)
        cursor.execute("SELECT location_id FROM location_aliases WHERE alias_normalized = ?", (norm_name,))
        existing = cursor.fetchone()

        if not existing:
            cursor.execute(
                "INSERT OR IGNORE INTO locations (id, canonical_name, category, latitude, longitude, osm_id, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (osm_id, name, cat, lat, lon, osm_id, "OSM_OVERPASS")
            )
            cursor.execute(
                "INSERT INTO location_aliases (location_id, alias_normalized, alias_type, confidence) VALUES (?, ?, ?, ?)",
                (osm_id, norm_name, "osm_name", 1.0)
            )

            # Check alternative OSM name tags
            for alt_tag, atype in [("alt_name", "osm_alt"), ("official_name", "osm_official"), ("short_name", "osm_short"), ("name:en", "osm_en")]:
                alt_val = tags.get(alt_tag)
                if alt_val and alt_val.strip():
                    norm_alt = normalize_text(alt_val)
                    if norm_alt and norm_alt != norm_name:
                        cursor.execute(
                            "INSERT INTO location_aliases (location_id, alias_normalized, alias_type, confidence) VALUES (?, ?, ?, ?)",
                            (osm_id, norm_alt, atype, 0.95)
                        )
            inserted_osm += 1

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM locations")
    total_locs = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM location_aliases")
    total_aliases = cursor.fetchone()[0]

    logger.info(f"Database build complete: {DB_PATH}")
    logger.info(f"Total Locations: {total_locs} (OSM elements added: {inserted_osm})")
    logger.info(f"Total Search Aliases: {total_aliases}")
    conn.close()


if __name__ == "__main__":
    populate_database()
