/**
 * Minimal ambient declaration for the Google Maps JS API.
 *
 * The full @types/google.maps package is ~500KB of definitions for a surface
 * this app touches in one file. The map component is the only consumer and it
 * is small enough to review by hand, so a loose declaration is the better
 * trade than another dependency.
 */
declare const google: any;

interface Window {
  google?: any;
}
