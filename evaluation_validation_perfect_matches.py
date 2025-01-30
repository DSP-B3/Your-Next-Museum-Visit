from datetime import datetime
from recommenders import *
from data import *
from tqdm import tqdm


def generate_sample(sample_size: int, number_of_visits_lowerbound: int):
    # Read the CSV and extract the "PersonID" column as a one-column dataFrame
    personid_df = pd.read_csv("data/members.csv", usecols=["PersonID"])

    personid_visits_df = (
        pd.read_csv("data/visits.csv", usecols=["PersonID"])
        .groupby("PersonID")
        .size()
        .reset_index(name="Visits")
    )

    # Left join the two dataFrames on the "PersonID" column
    merged_df = pd.merge(personid_df, personid_visits_df, on="PersonID", how="left")

    # Fill '0' for 'Visits' where the value is NaN
    merged_df["Visits"] = merged_df["Visits"].fillna(0).astype(int)

    # Filter the dataFrame to only include users with at least 'number_of_visits_lowerbound' visits
    merged_df = merged_df[merged_df["Visits"] >= number_of_visits_lowerbound]

    # From the remaining users, randomly sample 'sample_size' users
    sample = merged_df.sample(sample_size)

    # Get a list of 'User' objects from the sampled 'PersonID's with a progress bar
    sample = [
        User(person_id)
        for person_id in tqdm(sample["PersonID"], desc="Generating sample (step 1/2)")
    ]

    return sample


def write_scores_truth_table(
    sample_size: int,
    number_of_visits_lowerbound: int,
    test_split_size: float,
    recommender_method: str = "local_spots",
    max_distance_km: float = 15.0,  # Maximum allowed distance for "local spots"
):
    # There must be at least 1 museum in the test set
    if (number_of_visits_lowerbound * test_split_size < 1) and recommender_method != "local_spots":
        raise ValueError(
            "The test set must contain at least 1 museum. Please adjust the number_of_visits_lowerbound and test_split_size."
        )

    sample = generate_sample(sample_size, number_of_visits_lowerbound)

    r = RecSystem()

    tp_count = 0
    fn_count = 0

    # Add a progress bar for processing each user in the sample
    for user in tqdm(
        sample, desc="Getting recommendations and comparing to test set (step 2/2)"
    ):
        test_visits = user.split_previous_visits(test_split_size)

        if recommender_method == "perfect_matches":
            # Get the recommendations based on the train set
            recommendations = r.perfect_matches(user)
        elif recommender_method == "random":
            recommendations = r.n_random_museums(5)
        elif recommender_method == "local_spots":
            recommendations = r.local_spots(user)

        if recommender_method == "perfect_matches" or recommender_method == "random":
            # Calculate the TPs, FPs, FNs for perfect_matches
            for visit in test_visits:
                if visit[0].id3 in [
                    recommendation.id3 for recommendation in recommendations
                ]:
                    tp_count += 1
                else:
                    fn_count += 1

        elif recommender_method == "local_spots":
            user_coord = get_city_coordinates(user.residence)
            for recommendation in recommendations:
                rec_coord = get_city_coordinates(recommendation.city)
                if haversine(user_coord, rec_coord) <= max_distance_km:
                    # Recommendation is within range
                    tp_count += 1
                else:
                    # Recommendation is out of range
                    fn_count += 1

    recall = tp_count / (tp_count + fn_count)

    # Write the scores to a CSV file
    with open("data/scores_truth_table.csv", "a") as file:
        file.write(
            f"{datetime.now()},{recommender_method},{sample_size},{number_of_visits_lowerbound},{test_split_size},{tp_count},,{fn_count},,{recall},\n"
        )

    print("Scores written to 'scores_truth_table.csv'.")


# datetime,recommender_method,sample_size,number_of_visits_lowerbound,test_split_size,TP,FP,FN,precision,recall,remark


write_scores_truth_table(2000, 6, 0.2, "local_spots")

write_scores_truth_table(2000, 6, 0.2, "random")
