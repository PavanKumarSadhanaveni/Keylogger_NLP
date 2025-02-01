import React, { useState, useEffect } from "react";
import axios from "axios";
import DatePicker from "react-date-picker";
import "react-date-picker/dist/DatePicker.css";
import "react-calendar/dist/Calendar.css";
import { Wordcloud } from "@visx/wordcloud";
// import { scaleLinear } from 'd3-scale';
import { scaleOrdinal } from 'd3-scale';
import { schemeCategory10 } from 'd3-scale-chromatic';
import 'bootstrap/dist/css/bootstrap.min.css'; // Import Bootstrap CSS

interface Word {
  text: string;
  value: number;
}

interface KeylogWordsProps {
  // Define any props if needed, otherwise it's an empty interface
}
const colorScale = scaleOrdinal(schemeCategory10);
const KeylogWords: React.FC<KeylogWordsProps> = () => {
  const [startDate, setStartDate] = useState<Date>(
    new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
  ); // Default: past week
  const [endDate, setEndDate] = useState<Date>(new Date());
  const [words, setWords] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [wordCloud, setWordCloud] = useState<Word[]>([]);

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
      // Assuming the backend returns an array of strings
      setWords(response.data as string[]);
    } catch (err: any) {
      setError("Error fetching words data. Please try again later.");
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
      // Assuming the backend returns an array of objects {text: string, value: number}
      setWordCloud(response.data as Word[]);
    } catch (err: any) {
      setError("Error fetching word cloud data. Please try again later.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWords();
    fetchFreqForWordCloud(); // Fetch word cloud data on date change as well
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startDate, endDate]); // Re-fetch when dates change


  return (
    <div className="container mt-4"> {/* Bootstrap container for padding and responsiveness */}
      <h1 className="mb-4">Keylogged Words</h1> {/* Increased bottom margin */}

      <div className="row mb-3"> {/* Bootstrap row for date pickers */}
        <div className="col-md-6"> {/* Adjust column size as needed */}
          <div className="form-group"> {/* Bootstrap form group for labels and inputs */}
            <label htmlFor="startDate" className="form-label">Start Date:</label> {/* Bootstrap form label */}
            <DatePicker
              id="startDate"
              value={startDate}
              onChange={(date) => setStartDate(date as Date)}
              maxDate={endDate}
              className="form-control" // Basic form control styling - might need custom styling for react-date-picker
            />
          </div>
        </div>
        <div className="col-md-6">
          <div className="form-group">
            <label htmlFor="endDate" className="form-label">End Date:</label>
            <DatePicker
              id="endDate"
              value={endDate}
              onChange={(date) => setEndDate(date as Date)}
              minDate={startDate}
              maxDate={new Date()}
              className="form-control" // Basic form control styling - might need custom styling for react-date-picker
            />
          </div>
        </div>
      </div>

      {/* Button is kept for manual refresh if needed, or can be removed if auto-update is sufficient */}
      <button onClick={() => { fetchWords(); fetchFreqForWordCloud(); }} disabled={loading} className="btn btn-primary mb-3 " style={{display: 'flex'}}> {/* Bootstrap button styling and margin */}
        {loading ? "Fetching..." : "Fetch Words"}
      </button>

      {error && <div className="alert alert-danger">{error}</div>} {/* Bootstrap error alert */}

      <h2 className="mt-3">Words:</h2> {/* Top margin for spacing */}
      {words.length > 0 ? (
        <p className="border p-3 rounded"> {/* Added border, padding, and rounded corners for word list */}
          {words.map((word, index) => (
            <span key={index} className="badge bg-secondary me-1">{word} </span> // Display each word as a badge with margin
          ))}
        </p>
      ) : (
        <p>No words found for the selected period.</p>
      )}
      <h2 className="mt-3">Word Cloud:</h2> {/* Top margin for spacing */}
      {wordCloud.length > 0 ? (
        <div className="border p-3 rounded d-flex justify-content-center"> {/* Container for word cloud with border, padding, rounded corners and centering */}
          <Wordcloud
            width={600}
            height={400}
            words={wordCloud}
            fontSize={(word) => Math.sqrt(word.value) * 20} // Adjust font scaling as needed
            padding={5}
          >
            {(cloudWords) =>
              cloudWords.map((w, i) => (
                  <text
                  key={i}
                  style={{
                    fontSize: `${w.size}px`,
                    fontFamily: 'sans-serif',
                    fill: colorScale(w.text || "") as string,
                  }}
                  textAnchor="middle"
                  transform={`translate(${w.x}, ${w.y}) rotate(${w.rotate})`}
                  >
                  {w.text}
                  </text>
              ))
            }
          </Wordcloud>
        </div>
      ) : (
        <p>No word cloud data found for the selected period.</p>
      )}

    </div>
  );
}

export default KeylogWords;