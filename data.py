from collections import namedtuple
from dataclasses import dataclass
import os
import re
import sys
import pandas as pd
import spacy

# Ensure that the data is loaded only once
members_df = pd.read_csv(
    "data/members.csv",
    usecols=["PersonID", "Woonplaats", "Provincie", "Leeftijd"],
)
visits_df = pd.read_csv(
    "data/visits.csv",
    usecols=[
        "PersonID",
        "BezoekDatum",
        "MuseumCode",
        "MuseumNaam",
    ],
)
# If the user has visited a museum more than once, we only keep the most recent visit
visits_df = visits_df.sort_values(by=["PersonID", "BezoekDatum"], ascending=False)
visits_df = visits_df.drop_duplicates(subset=["PersonID", "MuseumNaam"])

museums_df = pd.read_csv("data/museums.csv")
museums_df = museums_df[museums_df["language"] == "nl"]
museums_df["city"] = museums_df["city"].str.lower()

# List of museums which no longer exists, so we remove them from the dataset
old_museums = ["Wereld van Wenters"]
museums_df = museums_df[~museums_df["publicName"].isin(old_museums)]

events_df = pd.read_csv("data/events.csv")
topics_df = pd.read_csv("data/topics.csv")

# Load the Dutch language model
NLP_DUTCH = spacy.load("nl_core_news_sm")


def is_valid_img_uuid(uuid_str: str) -> bool:
    # There should be an image named {uuid}.jpg in the static/museum_images folder
    return os.path.exists(f"static/museum_images/{uuid_str}.jpg")


class User:
    person_id: str = None
    residence: str = None
    age: int = None
    previous_visits: list = None

    def __init__(self, person_id: str):
        self.person_id = person_id

        personal_df = members_df[members_df.PersonID == person_id]
        self.residence = personal_df.Woonplaats.values[0]
        self.age = personal_df.Leeftijd.values[0]

        # For the user class, we only need a subset of columns
        part_of_museums_df = museums_df[
            ["publicName", "city", "description", "mainCategory", "subCategory", "id"]
        ]
        personal_visits_df = visits_df[visits_df.PersonID == person_id]

        museums_visited = pd.merge(
            left=part_of_museums_df,
            right=personal_visits_df,
            left_on="publicName",
            right_on="MuseumNaam",
            how="inner",
        )
        museums_visited = museums_visited.drop(
            columns=["PersonID", "MuseumNaam", "BezoekDatum"]
        )
        museums_visited = [
            Museum(
                id2=None,
                type=None,
                teaser=None,
                metaDescription=None,
                description=row["description"],
                kidsDescription=None,
                museumColor=None,
                showpieceIds=None,
                impressionCarrousel=None,
                museumHighlightsCarrousel=None,
                stbId=None,
                organisationCode=None,
                publicName=row["publicName"],
                mainCategory=row["mainCategory"],
                subCategory=row["subCategory"],
                website=None,
                modificationDateTimeUtc=None,
                streetName=None,
                streetNumber=None,
                streetNumberAddition=None,
                postalCode=None,
                city=row["city"],
                province=None,
                phoneNumber=None,
                lat=None,
                lng=None,
                museumCardFromDateTime=None,
                museumCardToDateTime=None,
                openingPeriods=None,
                urlOpeningHours=None,
                facilities=None,
                museumkids=None,
                latestMuseumKidsType=None,
                prizes=None,
                urlAdmissionFees=None,
                published=None,
                lastModifiedOn=None,
                createdOn=None,
                language=None,
                id3=row["id"],
                created=None,
                modified=None,
            )
            for _, row in museums_visited.iterrows()
        ]

        self.previous_visits = [
            PreviousVisit(museum=museum, timestamp=timestamp)
            for museum, timestamp in zip(
                museums_visited,
                pd.to_datetime(visits_df["BezoekDatum"], format="%Y%m%d"),
            )
        ]
        self.previous_visits = sorted(
            self.previous_visits, key=lambda visit: visit.timestamp
        )

    def get_interests_museums(self):
        # Get the main and sub categories of museums visited by the user and save them as a tuple in the list of interests gathered through museum categories
        interests_museums = [
            (previous_visit.museum.mainCategory, previous_visit.museum.subCategory)
            for previous_visit in self.previous_visits
        ]
        return interests_museums

    def get_museum_description_nouns(self):
        museum_description_nouns = []
        for previous_visit in self.previous_visits:
            museum_description_nouns += previous_visit.museum.description_nouns
        return museum_description_nouns

    def set_museum_description_nouns(self):
        return set(self.get_museum_description_nouns())

    def split_previous_visits(self, test_size: float):
        """
        Splits the previous_visits into train and test sets based on chronological order.

        Parameters:
        test_size (float): Proportion of the data to use as the test set (e.g., 0.2 for 20%). Since our recommender system outputs 5 recommendations, the test set size should not exceed 5.

        Returns:
        list: The test set (most recent visits).
        """
        if not (0 < test_size < 1):
            raise ValueError("test_size must be a float between 0 and 1.")

        total_visits = len(self.previous_visits)
        test_count = int(total_visits * test_size)

        # Ensure the test set size does not exceed 5
        test_count = min(test_count, 5)

        # Split the data into train and test
        test_visits = self.previous_visits[-test_count:]
        train_visits = self.previous_visits[:-test_count]

        # Update the train part to the User object
        self.previous_visits = train_visits

        return test_visits


RecommendationResult = namedtuple("RecommendationResult", ["museum", "score"])
PreviousVisit = namedtuple("PreviousVisit", ["museum", "timestamp"])
Topic = namedtuple("Topic", ["id", "title"])


@dataclass
class Museum:
    id2: any
    type: any
    teaser: any
    metaDescription: any
    description: any
    kidsDescription: any
    museumColor: any
    showpieceIds: any
    impressionCarrousel: any
    museumHighlightsCarrousel: any
    stbId: any
    organisationCode: any
    publicName: any
    mainCategory: any
    subCategory: any
    website: any
    modificationDateTimeUtc: any
    streetName: any
    streetNumber: any
    streetNumberAddition: any
    postalCode: any
    city: any
    province: any
    phoneNumber: any
    lat: any
    lng: any
    museumCardFromDateTime: any
    museumCardToDateTime: any
    openingPeriods: any
    urlOpeningHours: any
    facilities: any
    museumkids: any
    latestMuseumKidsType: any
    prizes: any
    urlAdmissionFees: any
    published: any
    lastModifiedOn: any
    createdOn: any
    language: any
    id3: any
    created: any
    modified: any

    distance_from_user: float = None
    prev_visit: bool = False
    _image_url: str = None

    @property
    def image_url(self):
        if self._image_url:
            return self._image_url

        uuid_regex = r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"
        mc = self.impressionCarrousel.replace("'", '"')

        for match in re.finditer(uuid_regex, mc):
            if is_valid_img_uuid(match.group()):
                self._image_url = f"/static/museum_images/{match.group()}.jpg"
                return f"/static/museum_images/{match.group()}.jpg"

        print(f"No image found for museum {self.publicName}", file=sys.stdout)
        return None

    @property
    def event_topics(self):
        # Filter events for language 'nl'
        events_df_nl = events_df[events_df["language"] == "nl"]
        # Filter events by museum ID
        museum_objects = events_df_nl[events_df_nl["museumId"] == self.id3]

        # Flatten all topic IDs into a list
        all_topic_ids = []
        for topic_list in museum_objects["topicIds"]:
            # Assuming topicIds are stored as a string representation of a list, e.g., "[1, 2, 3]"
            topic_ids = eval(topic_list) if isinstance(topic_list, str) else topic_list
            all_topic_ids.extend(topic_ids)

        # Count occurrences of each topic ID
        topic_counts = pd.Series(all_topic_ids).value_counts().to_dict()

        # Build the list of tuples with Topic namedtuple and counts
        topics_list = []
        for topic_id, count in topic_counts.items():
            title = topics_df.loc[topics_df["id"] == topic_id, "title"].values[0]
            topic = Topic(id=topic_id, title=title)
            topics_list.append((topic, count))

        return topics_list

    @property
    def events(self):
        # Filter events for language 'nl'
        events_df_nl = events_df[events_df["language"] == "nl"]
        # Filter events by museum ID
        museum_objects = events_df_nl[events_df_nl["museumId"] == self.id3]
        museum_objects["endDate"] = pd.to_datetime(
            museum_objects["endDate"], errors="coerce"
        )
        museum_objects["endDate"] = museum_objects["endDate"].apply(
            lambda x: x.replace(tzinfo=None) if pd.notnull(x) else x
        )
        museum_objects = museum_objects[
            museum_objects["endDate"] > pd.Timestamp.now().replace(tzinfo=None)
        ]
        return [
            Event(
                name=row["name"],
                id=row["id"],
                description=row["description"],
                startDate=row["startDate"],
                endDate=row["endDate"],
                museumId=row["museumId"],
            )
            for _, row in museum_objects.iterrows()
        ]

    @property
    def description_nouns(self):
        # If description is of type float, convert it to string
        if isinstance(self.description, float):
            self.description = str(self.description)

        doc = NLP_DUTCH(self.description)
        return [
            token.text
            for token in doc
            if (
                len(token.text) >= 3
                and token.pos_ == "NOUN"
                and token.text not in ["museum", "musea", "Museum", "Musea", "#", "‘"]
            )
            or token.text.isnumeric()
            and len(token.text) in [2, 4]
        ]


@dataclass
class Event:
    name: any
    id: any
    description: any
    startDate: any
    endDate: any
    museumId: any
