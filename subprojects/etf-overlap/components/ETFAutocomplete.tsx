"use client";

import { useState, useEffect, useRef, KeyboardEvent } from "react";

interface ETFListItem {
  symbol: string;
  name: string;
}

interface ETFAutocompleteProps {
  selectedETFs: string[];
  onChange: (etfs: string[]) => void;
  disabled?: boolean;
}

export default function ETFAutocomplete({
  selectedETFs,
  onChange,
  disabled,
}: ETFAutocompleteProps) {
  const [inputValue, setInputValue] = useState("");
  const [suggestions, setSuggestions] = useState<ETFListItem[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch suggestions as user types
  useEffect(() => {
    const fetchSuggestions = async () => {
      if (inputValue.trim().length === 0) {
        setSuggestions([]);
        setShowSuggestions(false);
        return;
      }

      try {
        const response = await fetch(
          `/api/search-etfs?q=${encodeURIComponent(inputValue)}`
        );
        const data = await response.json();

        if (data.results) {
          // Filter out already selected ETFs
          const filtered = data.results.filter(
            (etf: ETFListItem) => !selectedETFs.includes(etf.symbol)
          );
          setSuggestions(filtered);
          setShowSuggestions(filtered.length > 0);
        }
      } catch (error) {
        console.error("Error fetching suggestions:", error);
      }
    };

    const timeoutId = setTimeout(fetchSuggestions, 150); // Debounce
    return () => clearTimeout(timeoutId);
  }, [inputValue, selectedETFs]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const addETF = (symbol: string) => {
    if (!selectedETFs.includes(symbol)) {
      onChange([...selectedETFs, symbol]);
    }
    setInputValue("");
    setSuggestions([]);
    setShowSuggestions(false);
    setSelectedIndex(-1);
    inputRef.current?.focus();
  };

  const removeETF = (symbol: string) => {
    onChange(selectedETFs.filter((s) => s !== symbol));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) =>
        prev < suggestions.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (selectedIndex >= 0 && suggestions[selectedIndex]) {
        addETF(suggestions[selectedIndex].symbol);
      } else if (inputValue.trim().length > 0) {
        // User pressed Enter without selecting from dropdown
        addETF(inputValue.trim().toUpperCase());
      }
    } else if (e.key === " ") {
      // Space key - add current input as tag
      if (inputValue.trim().length > 0) {
        e.preventDefault();
        addETF(inputValue.trim().toUpperCase());
      }
    } else if (
      e.key === "Backspace" &&
      inputValue === "" &&
      selectedETFs.length > 0
    ) {
      // Backspace on empty input - remove last tag
      e.preventDefault();
      removeETF(selectedETFs[selectedETFs.length - 1]);
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
      setSelectedIndex(-1);
    }
  };

  return (
    <div style={{ position: "relative", width: "100%" }}>
      {/* Container for tags and input */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "0.5rem",
          padding: "0.5rem",
          border: "1px solid #ddd",
          borderRadius: "4px",
          minHeight: "50px",
          backgroundColor: disabled ? "#f5f5f5" : "white",
          cursor: disabled ? "not-allowed" : "text",
        }}
        onClick={() => inputRef.current?.focus()}
      >
        {/* Selected ETF tags */}
        {selectedETFs.map((symbol) => (
          <div
            key={symbol}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.375rem 0.75rem",
              backgroundColor: "#0070f3",
              color: "white",
              borderRadius: "4px",
              fontSize: "0.875rem",
              fontWeight: "500",
            }}
          >
            {symbol}
            {!disabled && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeETF(symbol);
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "white",
                  cursor: "pointer",
                  padding: "0",
                  fontSize: "1rem",
                  lineHeight: "1",
                }}
                aria-label={`Remove ${symbol}`}
              >
                ×
              </button>
            )}
          </div>
        ))}

        {/* Input field */}
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value.toUpperCase())}
          onKeyDown={handleKeyDown}
          onFocus={() => inputValue.length > 0 && setShowSuggestions(true)}
          placeholder={
            selectedETFs.length === 0
              ? "Type ETF ticker or name (e.g., SPY, QQQ)..."
              : ""
          }
          disabled={disabled}
          style={{
            flex: "1",
            minWidth: "200px",
            border: "none",
            outline: "none",
            fontSize: "1rem",
            backgroundColor: "transparent",
          }}
        />
      </div>

      {/* Autocomplete dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div
          ref={dropdownRef}
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            marginTop: "0.25rem",
            backgroundColor: "white",
            border: "1px solid #ddd",
            borderRadius: "4px",
            boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
            maxHeight: "300px",
            overflowY: "auto",
            zIndex: 1000,
          }}
        >
          {suggestions.map((etf, index) => (
            <div
              key={etf.symbol}
              onClick={() => addETF(etf.symbol)}
              onMouseEnter={() => setSelectedIndex(index)}
              style={{
                padding: "0.75rem",
                cursor: "pointer",
                backgroundColor: selectedIndex === index ? "#eff6ff" : "white",
                borderBottom:
                  index < suggestions.length - 1 ? "1px solid #f3f4f6" : "none",
              }}
            >
              <div style={{ fontWeight: "600", color: "#1f2937" }}>
                {etf.symbol}
              </div>
              <div
                style={{
                  fontSize: "0.875rem",
                  color: "#6b7280",
                  marginTop: "0.125rem",
                }}
              >
                {etf.name}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Hint text */}
      <div
        style={{ fontSize: "0.75rem", color: "#9ca3af", marginTop: "0.5rem" }}
      >
        💡 Type to search, press Space or Enter to add, Backspace to remove
      </div>
    </div>
  );
}
