import React, { useState, useEffect } from "react";
import axios from "axios";
import DatePicker from "react-date-picker";
import "react-date-picker/dist/DatePicker.css";
import "react-calendar/dist/Calendar.css";
import ReactWordcloud from "react-wordcloud";

function KeylogWords() {
  const [startDate, setStartDate] = useState(
    new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
  ); // Default: past week
  const [endDate, setEndDate] = useState(new Date());
  const [words, setWords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [wordCloud, setWordCloud] = useState([]);

  const fetchWords = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get("http://localhost:5000/api/words", {
        params: {
          startDate: startDate.toISOString(),
          endDate: endDate.toISOString(),
        },
      });
      setWords(response.data);
    } catch (err) {
      setError("Error fetching data. Please try again later.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFreqForWordCloud = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get("http://localhost:5000/api/wordcloud", {
        params: {
          startDate: startDate.toISOString(),
          endDate: endDate.toISOString(),
        },
      });
      setWordCloud(response.data);
    } catch (err) {
      setError("Error fetching data. Please try again later.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWords();
  }, [startDate, endDate]);

  useEffect(() => {
    fetchFreqForWordCloud();
  }, [startDate, endDate]);
  const options = {
    rotations: 2,
    rotationAngles: [-90, 0],
  };

  return (
    <div>
      <h1>Keylogged Words</h1>

      <div>
        <label htmlFor="startDate">Start Date:</label>
        <DatePicker
          id="startDate"
          value={startDate}
          onChange={setStartDate}
          maxDate={endDate} // Prevent selecting start date after end date
        />
      </div>
      <div>
        <label htmlFor="endDate">End Date:</label>
        <DatePicker
          id="endDate"
          value={endDate}
          onChange={setEndDate}
          minDate={startDate} // Prevent selecting end date before start date
          maxDate={new Date()}
        />
      </div>

      <button onClick={()=>{fetchWords();fetchFreqForWordCloud();}} disabled={loading}>
        {loading ? "Fetching..." : "Fetch Words"}
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <h2>Words:</h2>
      {words.length > 0 ? (
        <p>
          {words.map((wordObj, index) => (
            <span key={index}>{wordObj} </span> // Display each word
          ))}
        </p>
      ) : (
        <p>No words found for the selected period.</p>
      )}
      <h2>Word Cloud:</h2>
      <ReactWordcloud words={wordCloud} size={[600,400]} options={options}/>
    </div>
  );
}

export default KeylogWords;
