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
import { deriveKey, encryptData, decryptData } from './encryption';
import CryptoJS from 'crypto-js';

interface Word {
  text: string;
  value: number;
}

interface FuzzyMatch {
  timestamp: string;
  userId: string;
  flaggedWord: string;
  screenshot_url: string | null;
  flagged_word_similar_to: string | null;
  category?: string | null;
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

  const [passphrase, setPassphrase] = useState<string>('');
  const [encryptionKey, setEncryptionKey] = useState<CryptoJS.lib.WordArray | null>(null);
  // const [salt, setSalt] = useState<string>(''); // Removed salt

  // New state for user selection
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [availableUserIds, setAvailableUserIds] = useState<string[]>([]);

  // useEffect(() => { // Removed salt fetching effect
  //   const fetchSalt = async () => {
  //     try {
  //       const response = await axios.get("/api/salt");
  //       const data = response.data;
  //       setSalt(data.salt);
  //       console.log("Fetched Salt (Frontend):", data.salt);
  //     } catch (error) {
  //       console.error("Failed to fetch salt:", error);
  //     }
  //   };

  //   fetchSalt();
  // }, []);

  useEffect(() => {
    if (passphrase) { // Removed salt dependency
      // Derive the key using the passphrase (no salt needed now)
      const key = deriveKey(passphrase);
      setEncryptionKey(key);
    } else {
      setEncryptionKey(null); // Clear the key if passphrase is missing
    }
  }, [passphrase]); // Re-run when passphrase changes

  const fetchWords = async () => {
    setLoading(true);
    setError(null);
    if (!encryptionKey) {
      setError("Encryption key not set.");
      setLoading(false);
      return;
    }
    try {
      // Encrypt start and end dates (existing)
      const encryptedStartDate = encryptData(startDate.toISOString(), encryptionKey);
      const encryptedEndDate = encryptData(endDate.toISOString(), encryptionKey);
      // Encrypt userId if selected
      const encryptedUserId = selectedUserId ? encryptData(selectedUserId, encryptionKey) : null;


      const response = await axios.get("/api/words", {
        params: {
          startDate: encryptedStartDate,
          endDate: encryptedEndDate,
          userId: encryptedUserId, // Send encrypted userId
        },
        headers: {
          'X-Passphrase': passphrase,
        }
      });

      const decryptedWords = response.data.map((word: string) =>
        decryptData(word, encryptionKey)
      );
      setWords(decryptedWords);

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
    if (!encryptionKey) {
      setError("Encryption key not set.");
      setLoading(false);
      return;
    }
    try {
      // Encrypt start and end dates (existing)
      const encryptedStartDate = encryptData(startDate.toISOString(), encryptionKey);
      const encryptedEndDate = encryptData(endDate.toISOString(), encryptionKey);
      // Encrypt userId if selected
      const encryptedUserId = selectedUserId ? encryptData(selectedUserId, encryptionKey) : null;


      const response = await axios.get("/api/wordcloud", {
        params: {
          startDate: encryptedStartDate,
          endDate: encryptedEndDate,
          userId: encryptedUserId, // Send encrypted userId
        },
        headers: {
          'X-Passphrase': passphrase,
        }
      });
      const decryptedWordCloud = response.data.map((word: any) => ({
        text: decryptData(word.text, encryptionKey),
        value: word.value,
      }));

      setWordCloud(decryptedWordCloud);
    } catch (err: any) {
      setError("Error fetching word cloud data. Please try again later.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFuzzyMatches = async () => {
    if (!hasMore || loadingFuzzyMatches) return;

    setLoadingFuzzyMatches(true);
    setError(null);
    if (!encryptionKey) {
      setError("Encryption key not set.");
      setLoadingFuzzyMatches(false);
      return;
    }
    try {
      // Encrypt start and end dates (existing)
      const encryptedStartDate = encryptData(startDate.toISOString(), encryptionKey);
      const encryptedEndDate = encryptData(endDate.toISOString(), encryptionKey);
      // Encrypt userId if selected
      const encryptedUserId = selectedUserId ? encryptData(selectedUserId, encryptionKey) : null;


      const response = await axios.get("/api/fuzzy-matches", {
        params: {
          startDate: encryptedStartDate,
          endDate: encryptedEndDate,
          userId: encryptedUserId, // Send encrypted userId
          cacheBuster: Date.now(),
        },
        headers: {
          'X-Passphrase': passphrase,
        }
      });

      const newMatches = response.data as FuzzyMatch[];

      if (newMatches.length === 0) {
        setHasMore(false);
      }

      setFuzzyMatches(prevMatches => {
        const decryptedNewMatches = newMatches.map(match => ({
          ...match,
          timestamp:match.timestamp,
          userId: decryptData(match.userId, encryptionKey,), // Decrypt userId here
          flaggedWord: decryptData(match.flaggedWord, encryptionKey,),
          flagged_word_similar_to: match.flagged_word_similar_to ? decryptData(match.flagged_word_similar_to, encryptionKey,) : null,
          category: match.category ? decryptData(match.category, encryptionKey,) : null,
          // screenshot_url is NOT encrypted, it's a URL
        }));

        const allMatches = [...prevMatches, ...decryptedNewMatches];
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
    // SSE event listener
    const eventSource = new EventSource('/api/stream');

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("Received SSE event:", data);

      if (encryptionKey) {
        // Decrypt userId in SSE event
        const decryptedUserId = decryptData(data.userId, encryptionKey);

        if (Notification.permission === 'granted') {
          const notificationTitle = `Offensive word detected: ${data.flaggedWord}`;
          const notificationOptions = {
            body: `User: ${decryptedUserId}\nClick to view.`, // Use decrypted userId
            data: { url: "/" },
          };

          navigator.serviceWorker.ready.then(registration => {
            registration.showNotification(notificationTitle, notificationOptions);
          });
        }
      } else {
        console.warn("Encryption key not available, cannot decrypt userId from SSE event.");
        // Handle case where encryptionKey is null, e.g., set decryptedUserId to null or original userId
      }
    };

    eventSource.onerror = (error) => {
      console.error("EventSource failed:", error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [encryptionKey]); // Add encryptionKey as dependency


  // Fetch available user IDs on component mount
  useEffect(() => {
    const fetchUserIds = async () => {
      try {
        const response = await axios.get('/api/users', {
          headers: {
            'X-Passphrase': passphrase,
          }
        });
        if (encryptionKey) {
          // Decrypt userIds received from backend
          const decryptedUserIds = response.data.map((userId: string) => decryptData(userId, encryptionKey));
          setAvailableUserIds(decryptedUserIds);
        } else {
          console.warn("Encryption key not available, cannot decrypt user IDs.");
          setAvailableUserIds(response.data); // Or handle differently if decryption is mandatory
        }
      } catch (error) {
        console.error("Error fetching user IDs:", error);
        setError("Failed to load user IDs.");
      }
    };

    if (passphrase) {
      fetchUserIds();
    }
  }, [passphrase, encryptionKey]); // Add encryptionKey as dependency


  useEffect(() => {
    fetchWords();
    fetchFreqForWordCloud();
  }, [startDate, endDate, encryptionKey, selectedUserId]);

  useEffect(() => {
    setFuzzyMatches([]);
    setPage(0);
    setHasMore(true);
    fetchFuzzyMatches();
  }, [startDate, endDate, encryptionKey, selectedUserId]);

  useEffect(() => {
    if (page > 0) {
      fetchFuzzyMatches();
    }
  }, [page]);


  return (
    <div className="container mt-4">
      <h1>Keylogged Words</h1>

      <div className="mb-3">
        <label htmlFor="passphrase">Passphrase:</label>
        <input
          type="password"
          id="passphrase"
          className="form-control"
          value={passphrase}
          onChange={(e) => setPassphrase(e.target.value)}
        />
      </div>

      {/* User Chooser Dropdown */}
      <div className="mb-3">
        <label htmlFor="userId">Select User:</label>
        <select
          id="userId"
          className="form-control"
          value={selectedUserId || ''}
          onChange={(e) => setSelectedUserId(e.target.value === '' ? null : e.target.value)}
        >
          <option value="">All Users</option>
          {availableUserIds.map((userId) => (
            <option key={userId} value={userId}>{userId}</option>
          ))}
        </select>
      </div>


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
          <li key={index} className="list-group-item">
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
        {loadingFuzzyMatches && <li>Loading more matches...</li>}
        {!hasMore && fuzzyMatches.length > 0 && <li>No more matches to load.</li>}
        {error && <li className="error-message">Error: {error}</li>}
      </ul>
    </div>
  );
};

export default KeylogWords;