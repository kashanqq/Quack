"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { Duck } from "./Duck";
import styles from "./duck.module.css";

type Flight = {
  id: number;
  top: number;
  reversed: boolean;
  style: CSSProperties;
};

const rand = (min: number, max: number) => min + Math.random() * (max - min);

/** A duck crosses the screen at a random height roughly once a minute. */
export function FlyingDucks() {
  const [flights, setFlights] = useState<Flight[]>([]);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let timer: ReturnType<typeof setTimeout>;
    let nextId = 0;

    const launch = () => {
      const reversed = Math.random() < 0.5;
      const from = reversed ? window.innerWidth + 80 : -80;
      const to = reversed ? -80 : window.innerWidth + 80;
      const flight: Flight = {
        id: nextId++,
        top: rand(8, 78),
        reversed,
        style: {
          "--from": `${from}px`,
          "--to": `${to}px`,
          "--drift": `${rand(-60, 60)}px`,
          "--size": rand(0.8, 1.25).toFixed(2),
          "--duration": `${Math.round(rand(6000, 10000))}ms`,
        } as CSSProperties,
      };
      setFlights((list) => [...list, flight]);
    };

    const schedule = (delay: number) => {
      timer = setTimeout(() => {
        if (!document.hidden) launch();
        schedule(rand(45000, 75000));
      }, delay);
    };

    schedule(rand(15000, 40000));
    return () => clearTimeout(timer);
  }, []);

  return flights.map((flight) => (
    <div
      key={flight.id}
      className={`${styles.flying} ${flight.reversed ? styles.reversed : ""}`}
      style={{ ...flight.style, top: `${flight.top}vh` }}
      onAnimationEnd={(e) => {
        if (e.target === e.currentTarget) setFlights((list) => list.filter((f) => f.id !== flight.id));
      }}
      aria-hidden="true"
    >
      <div className={styles.bob}>
        <Duck wingClassName={styles.flapFast} />
      </div>
    </div>
  ));
}
