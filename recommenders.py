import random
from data import *
from math import radians, sin, cos, sqrt, atan2

BOOST = 1.5
N_RECS = 6
THRESHOLD = 0.2
QUANTILE = 0.90
OLD_MUSEUMS = [
    "Wereld van Wenters"
]  # These are not longer available, but are still sometimes in the dataset.

cities_df = pd.read_csv("data/cities_grouped.csv")

museums_short = pd.read_csv("data/museum_nouns_and_visits.csv")
popularity_threshold = museums_short["n_visits"].quantile(QUANTILE)
bottom_threshold = museums_short["n_visits"].quantile(0.25)

museums_dict = museums_short.set_index("publicName").to_dict("index")
for museum in museums_dict:
    museums_dict[museum]["Nouns"] = eval(museums_dict[museum]["Nouns"])


# Function to calculate distance using the Haversine formula
def haversine(coord1, coord2):
    """
    Calculate the great-circle distance between two points on the Earth.

    :param coord1: Tuple (latitude, longitude) for the first point.
    :param coord2: Tuple (latitude, longitude) for the second point.
    :return: Distance in kilometers.
    """
    # Convert latitude and longitude from degrees to radians
    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    radius_earth_km = 6371  # Radius of Earth in kilometers
    return radius_earth_km * c


# Function to get coordinates of a city
def get_city_coordinates(city_name):
    if isinstance(city_name, float):
        city_name = str(city_name)
    city_name = city_name.upper().replace("/", "").replace("'", "").replace("-", " ")
    # Find the entries in cities_df that match the city_name
    city = cities_df[cities_df.city == city_name]
    if city.empty:
        return (0, 0)
    return city.iloc[0].lat, city.iloc[0].lon


class RecSystem:
    def __init__(self):
        all_museums = pd.read_csv("data/museums.csv")
        all_museums = all_museums[all_museums.language == "nl"]
        all_museums = all_museums.dropna(subset=["city"])

        self.all_users = pd.read_csv("data/members.csv")

        all_museums["city"] = all_museums["city"].str.upper()

        all_museums = [Museum(*row) for row in all_museums.itertuples(index=False)]
        self.all_museums = [
            m
            for m in all_museums
            if m.published == True and m.publicName not in OLD_MUSEUMS
        ]

    def distance_to_all_museums(self, user_coords: str):
        city_distances = []

        # Calculate distances to all cities
        for city in set(museum.city for museum in self.all_museums):
            city_coords = get_city_coordinates(city)
            if city_coords == (0, 0):
                continue
            distance = haversine(user_coords, city_coords)
            city_distances.append((city, distance))

        return city_distances

    def n_random_museums(self, n: int) -> list[Museum]:
        return random.sample(self.all_museums, n)
    
    def get_relevant_museums(self, user: User) -> list[Museum]:
        relevant_museums = []
        for museum, time in user.previous_visits:
            if not len(museum.events) == 0:
                for event in museum.events:
                    if pd.to_datetime(event.startDate).replace(
                        tzinfo=None
                    ) > pd.to_datetime(time).replace(tzinfo=None):
                        relevant_museums.append(museum)
                        break
        prev_visits = [m[0].publicName for m in user.previous_visits]

        for museum in self.all_museums:
            if museum.publicName not in prev_visits:
                relevant_museums.append(museum)
        return relevant_museums

    def local_spots(self, user: User) -> list[Museum]:
        """
        Return the top 5 museums closest to the user's city that are not part of the top 10% of museums.
        (Low distance, med/low popularity)
        """

        user_coords = get_city_coordinates(user.residence)
        city_distances = self.distance_to_all_museums(user_coords)

        # Sort the cities by distance and get the five closest cities
        closest_cities = sorted(city_distances, key=lambda x: x[1])[:5]
        closest_city_names = [city for city, distance in closest_cities]

        relevant_museums = self.get_relevant_museums(user)

        # Filter museums in the closest cities
        closest_museums = [
            museum
            for museum in relevant_museums
            if museum.city in closest_city_names
        ]

        # Calculate distances to the museums in the closest cities
        distances = []
        for museum in closest_museums:
            popularity = museums_dict[museum.publicName]["n_visits"]
            if popularity < popularity_threshold:
                distance = haversine(user_coords, (museum.lat, museum.lng))
                distances.append((museum, distance))
                museum.distance_from_user = distance

        # Sort the museums by distance and return the top 5 closest museums
        closest_museums_sorted = sorted(distances, key=lambda x: x[1])[:N_RECS]

        museum_list = [museum for museum, distance in closest_museums_sorted if distance < 50]
        for museum in museum_list:
            if museum.publicName in user.previous_visits:
                museum.prev_visit = True

        return museum_list

    def hidden_gems(self, user: User) -> list[Museum]:
        """
        Return 5 museums that are in the bottom 25% of popularity and have high overlap with the user.
        (High interest, low popularity)
        """

        smaller_museums = [
            museum
            for museum in self.all_museums
            if museums_dict[museum.publicName]["n_visits"] <= bottom_threshold
        ]

        recs = {}
        user_nouns = user.get_museum_description_nouns()
        prev_visits = [m[0].publicName for m in user.previous_visits]

        relevant_museums = self.get_relevant_museums(user)
        rel_mus = []
        for museum in relevant_museums:
            rel_mus.append(museum.publicName)

        for museum in museums_dict.keys():

            score = 0

            if museum in rel_mus:
                museum_nouns = museums_dict[museum]["Nouns"]
                museum_l = len(set(museum_nouns))
                common_l = len(set(user_nouns) & set(museum_nouns))

                if museum_l > 0:
                    score += common_l / museum_l
                if score >= THRESHOLD:
                    recs[museum] = score

        # Sort the recommendations by score in descending order and return the top 5
        sorted_recs = sorted(recs.items(), key=lambda item: item[1], reverse=True)[:N_RECS]
        print(sorted_recs)

        # Find museum object in all_museums for all recommendations
        museum_list = []
        recommended_museums = [rec[0] for rec in sorted_recs]

        for museum_name in recommended_museums:
            for museum in self.all_museums:
                if museum.publicName == museum_name:
                    museum_list.append(museum)

                    # Set the prev_visit property to True if the museum was visited before
                    # This is to display the "New exibition" tag
                    if museum.publicName in prev_visits:
                        museum.prev_visit = True

        return museum_list

    def perfect_matches(self, user: User) -> list[tuple[Museum, float]]:
        """
        Return 5 museums that have the highest overlap with the user based on previous visits and location.
        (High interest, med/low distance)
        """
        user_coords = get_city_coordinates(user.residence)
        city_distances = self.distance_to_all_museums(user_coords)

        # Sort the cities by distance and get the five closest cities
        closest_cities = sorted(city_distances, key=lambda x: x[1])[:10]
        closest_city_names = [city for city, distance in closest_cities]

        # Filter museums in the closest cities
        closest_museums = [
            museum.publicName
            for museum in self.all_museums
            if museum.city in closest_city_names
        ]

        recs = {}
        user_nouns = user.get_museum_description_nouns()
        prev_visits = [m[0].publicName for m in user.previous_visits]
        relevant_museums = self.get_relevant_museums(user)
        rel_mus = []
        for museum in relevant_museums:
            rel_mus.append(museum.publicName)

        for museum in museums_dict.keys():
            score = 0

            if museum in rel_mus:
                museum_nouns = museums_dict[museum]["Nouns"]
                museum_l = len(set(museum_nouns))
                common_l = len(set(user_nouns) & set(museum_nouns))

                if museum_l > 0:
                    score += common_l / museum_l
                if museum in closest_museums:
                    score *= BOOST
                if score >= THRESHOLD:
                    recs[museum] = score

        # Sort the recommendations by score in descending order and return the top 5
        sorted_recs = sorted(recs.items(), key=lambda item: item[1], reverse=True)[:N_RECS]

        # Find museum object in all_museums for all recommendations
        museum_list = []
        recommended_museums = [rec[0] for rec in sorted_recs]

        for museum_name in recommended_museums:
            for museum in self.all_museums:
                if museum.publicName == museum_name:
                    museum_list.append(museum)

                    # Set the prev_visit property to True if the museum was visited before
                    # This is to display the "New exibition" tag
                    if museum.publicName in prev_visits:
                        museum.prev_visit = True

        if len(museum_list) < 5:
            additional_museums = self.local_spots(user)[: N_RECS - len(museum_list)]
            museum_list.extend(additional_museums)

        return museum_list
