import sys
import json
import datetime
import re
import unicodecsv as csv

def decode_dw_row(row):
    # decodes row such as:
    #  114   29774  71  24  CALIFOR    100  0  1   CAPPS         -0.389   -0.227      -81.84920   1077     26    0.927
    # format: congress, icpsr, state code, district number (0 if senate or president), state name, party code (100=dem, 200=republican), occupancy, office attainment type, name, 1st dimension coord, 2nd dimension coord, log likelyhood, # of votes, # of classification errors, geometric mean probability
    elements = [element.strip() for element in row.split("  ") if element.strip() != ""]
    if len(elements) != 15:
        print "error: != 15 elements in a row!"
        print row
        raise Exception("!= 15 elements in row")
    return {
        "congress": row[0],
        "icpsr": row[1],
        "state_code": row[2],
        "district_number": row[3],
        "state": row[4],
        "party_code": row[5],
        "occupancy": row[6],
        "office_attainment_type": row[7],
        "last_name": row[8].split(" ")[0],
        "dim_1": row[9],
        "dim_2": row[10],
        "log_likelyhood": row[11],
        "votes": row[12],
        "classification_errors": row[13],
        "geometric_mean_probability": row[14]
    }

def match(record):
    """
    Determine whether or not a record matches the search and should be included.
    """
    try:
        text = record["statement"].lower()
        title = record["title"]

        #date = datetime.datetime.strptime(record["date"], "%Y-%m-%d")
        #bio = record["bio"]
        #party = "Unknown"
        #name = record["speaker"]
        #if bio is not Null:
        #    if "party" in bio:
        #        party = bio['party']
        #    if "first_name" in bio and "last_name" in bio:
        #        name = bio["first_name"] + " " + bio["last_name"]

        # special logic

        # [!] match border unless Pakistan or Afghanistan is present
        if "border" in text:
            if not ("pakistan" in text or "afghan" in text):
                return False

        # [!] remove "american soil"  unless "foreign" or "somalia" or "afghanistan" or "pakistan" or "yemen" present
        if "american soil" in text:
            if not ("foreign" in text or "somalia" in text or "afghanistan" in text or "pakistan" in text or "yemen" in text):
                return False

        # general terms
        required = [
            re.compile("drone| uav |unmanned aerial vehicle")
        ]
        disallowed = [
            re.compile("(commerc|amazon|bezos|cargo|homeland security|dhs|faa|federal aviation administration|police|secret service|pipeline|survey)")
        ]
        for term in required:
            if not term.search(text):
                return False
        for term in disallowed:
            if term.search(text):
                return False

        return True
    except Exception as e:
        print e

output_columns = {
    "bio_columns": [
        "first_name",
        "last_name",
        "party",
        "sex",
        "days_until_term_ends",
        "state"
    ],
    "record_columns": [
        "date",
        "statement",
        "title",
        "id"
    ],
    "order": [
        "id",
        "date",
        "title",
        "first_name",
        "last_name",
        "party",
        "sex",
        "state",
        "days_until_term_ends",
        "statement"
    ]
}

def generate_row(record):
    row = []
    for column in output_columns['order']:
        value = "Unknown"
        if column in output_columns["bio_columns"]:
            if record['bio'] is not None:
                if column in record['bio']:
                    value = record['bio'][column]
        if column in output_columns['record_columns']:
            if column in record:
                value = record[column]
        row.append(value)
    return row

if len(sys.argv) < 3:
    print "Usage: <Annotated CGRecord (JSON) location> <output (JSON) location> [csv location]"
    sys.exit(0)

cgrecord_location = sys.argv[1]
output_location = sys.argv[2]
csv_location = None
if len(sys.argv) > 3:
    csv_location = sys.argv[3]

print "Loading annotated congressional record (this may take awhile)..."
records = []
with open(cgrecord_location, "r") as infile:
    records = json.load(infile)
print "Loaded {} records from the annotated congressional record!".format(str(len(records)))
print "Performing search..."
matched = []
for record in records:
    if match(record):
        matched.append(record)
print "Search completed... found {} matched records ({}% matched).".format(str(len(matched)), str((len(matched)+0.0)*100/len(records)))
print "Compiling output..."
output = []
for record in matched:
    trimmed_record = {}
    # try:
    if "bio" in record:
        for column in output_columns["bio_columns"]:
            if record["bio"] is not None and column in record["bio"]:
                trimmed_record[column] = record["bio"][column]
            else:
                trimmed_record[column] = "Unknown"
    for column in output_columns["record_columns"]:
        if column in record:
            trimmed_record[column] = record[column]
        else:
            trimmed_record[column] = "Unknown"
    output.append(trimmed_record)
    # except Exception as e:
    #     print e
    #     print "(moving on)"
print "Output compiled ({}/{} matched records included)".format(str(len(output)), str(len(matched)))
print "Writing JSON..."
with open(output_location, "w") as jsonout:
    json.dump(output, jsonout, indent=4)
if csv_location is not None:
    print "Writing CSV..."
    with open(csv_location, "w") as csvfile:
        writer = csv.writer(csvfile, encoding="utf-8")
        writer.writerow(output_columns["order"])
        for match in matched:
            writer.writerow(generate_row(match))
print "Done!"
