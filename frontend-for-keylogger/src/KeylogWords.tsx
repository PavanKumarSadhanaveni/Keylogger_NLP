import React, { useState, useEffect, useRef, useCallback } from "react";
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

interface FuzzyMatch {
  timestamp: string;
  userId: string;
  flaggedWord: string;
  screenshot_url: string | null;
  flagged_word_similar_to: string;
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

  // Fuzzy Matches and Lazy Loading
  const [fuzzyMatches, setFuzzyMatches] = useState<FuzzyMatch[]>([]);
  const [hasMore, setHasMore] = useState(true); // For infinite scroll
  const [page, setPage] = useState(0);         // Page number for lazy loading
  const [loadingFuzzyMatches, setLoadingFuzzyMatches] = useState(false);

  const observer = useRef<IntersectionObserver | null>(null); // Intersection Observer for lazy loading

  const lastMatchElementRef = useCallback((node: HTMLLIElement | null) => {
    if (loadingFuzzyMatches) return;
    if (observer.current) observer.current.disconnect();
    observer.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && hasMore) {
        setPage(prevPage => prevPage + 1); // Load next page
      }
    });
    if (node) observer.current.observe(node);
  }, [loadingFuzzyMatches, hasMore]);


  const fetchWords = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get("/api/words", { // Use relative URL
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
      const response = await axios.get("/api/wordcloud", { // Use relative URL
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

  const fetchFuzzyMatches = async () => {
      if (!hasMore || loadingFuzzyMatches) return; // Prevent multiple calls

      setLoadingFuzzyMatches(true);
      setError(null);
      try {
          const response = await axios.get("/api/fuzzy-matches", { // Use relative URL
              params: {
                  startDate: startDate.toISOString(),
                  endDate: endDate.toISOString(),
                  cacheBuster: Date.now(),
              },
          });

          const newMatches = response.data as FuzzyMatch[];

          if (newMatches.length === 0) {
              setHasMore(false); // No more data to load
          }

          setFuzzyMatches(prevMatches => {
              const allMatches = [...prevMatches, ...newMatches];
              const uniqueMatchesMap = new Map(allMatches.map(match => [match.timestamp, match]));
              const uniqueMatches = Array.from(uniqueMatchesMap.values()).sort(
                  (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
              );
              return uniqueMatches;
          });

      } catch (err: any) {
          setError("Error fetching fuzzy matches. Please try again later.");
          console.error(err);
      } finally {
          setLoadingFuzzyMatches(false);
      }
  };

    useEffect(() => {
        // Listen for SSE events
        const eventSource = new EventSource('/api/stream');

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("Received SSE event:", data);

            // Display a notification (even if the app is in the background,
            // the service worker will handle it)
            if (Notification.permission === 'granted') {
                const notificationTitle = `Offensive word detected: ${data.flaggedWord}`;
                const notificationOptions = {
                    body: `User: ${data.userId}\nClick to view.`, // Removed screenshot mention
                    // icon: data.screenshotUrl, // Removed icon
                    data: { url: "/" }, // Pass root URL for click handling
                };

                navigator.serviceWorker.ready.then(registration => {
                    registration.showNotification(notificationTitle, notificationOptions);
                });
            }
        };

        eventSource.onerror = (error) => {
            console.error("EventSource failed:", error);
            eventSource.close();
        };

        // Clean up the EventSource when the component unmounts
        return () => {
            eventSource.close();
        };
    }, []); // Empty dependency array: run only once on mount


  useEffect(() => {
    fetchWords();
    fetchFreqForWordCloud(); // Fetch word cloud data on date change as well
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startDate, endDate]); // Re-fetch when dates change

  useEffect(() => {
      setFuzzyMatches([]); // Clear previous matches when dates change
      setPage(0);
      setHasMore(true);
      fetchFuzzyMatches();
      // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startDate, endDate]); // Reset and re-fetch fuzzy matches when dates change

  useEffect(() => {
    if (page > 0) { // Only fetch more if page > 0 (avoid initial double fetch)
        fetchFuzzyMatches();
    }
      // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]); // Fetch more matches when page changes


  return (
    <div className="container mt-4">
      <h1>Keylogged Words</h1>

      <div className="row mb-3">
        <div className="col-md-6">
          <div className="form-group">
            <label htmlFor="startDate">Start Date:</label>
            <DatePicker
              id="startDate"
              value={startDate}
              onChange={(date) => setStartDate(date as Date)}
              maxDate={endDate}
              className="form-control"
            />
          </div>
        </div>
        <div className="col-md-6">
          <div className="form-group">
            <label htmlFor="endDate">End Date:</label>
            <DatePicker
              id="endDate"
              value={endDate}
              onChange={(date) => setEndDate(date as Date)}
              minDate={startDate}
              maxDate={new Date()}
              className="form-control"
            />
          </div>
        </div>
      </div>

      <button onClick={() => { fetchWords(); fetchFreqForWordCloud(); fetchFuzzyMatches(); }} disabled={loading} className="btn btn-primary mb-3">
        {loading ? "Fetching..." : "Fetch Data"}
      </button>

      {error && <div className="alert alert-danger">{error}</div>}

      <h2>Words:</h2>
      {words.length > 0 ? (
        <p className="border p-3 rounded">
          {words.map((word, index) => (
            <span key={index} className="badge bg-secondary me-1">{word}</span>
          ))}
        </p>
      ) : (
        <p>No words found for the selected period.</p>
      )}

      <h2>Word Cloud:</h2>
      {wordCloud.length > 0 ? (
        <div className="border p-3 rounded d-flex justify-content-center">
          <Wordcloud
            width={600}
            height={400}
            words={wordCloud}
            fontSize={(word) => Math.sqrt(word.value) * 20}
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

      <h2>Fuzzy Matches:</h2>
      <ul className="list-group">
        {fuzzyMatches.map((match, index) => (
          <li ref={index === fuzzyMatches.length - 1 ? lastMatchElementRef : undefined} key={index} className="list-group-item">
            <p><strong>Timestamp:</strong> {new Date(match.timestamp).toLocaleString()}</p>
            <p><strong>User:</strong> {match.userId}</p>
            <p><strong>Flagged Word:</strong> {match.flaggedWord}</p>
            {match.flagged_word_similar_to && (
              <p><strong>Similar to:</strong> {match.flagged_word_similar_to}</p>
            )}
            {match.screenshot_url && (
              <img src={match.screenshot_url} alt={`Screenshot for ${match.flaggedWord}`} className="img-fluid" />
            )}
          </li>
        ))}
        {loadingFuzzyMatches && <li className="list-group-item">Loading more...</li>}
        {!hasMore && <li className="list-group-item">No more matches to load.</li>}
      </ul>
    </div>
  );
};

export default KeylogWords;