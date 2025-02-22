self.addEventListener('push', (event) => {
  // Keep the service worker alive until the notification is created.
  event.waitUntil(
    self.registration.showNotification('Background Push Received', {
      body: event.data.text(), //  Get the data from the push event
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close(); // Close the notification

  // Example: Open a specific URL when the notification is clicked
  // You might want to customize this based on the notification data
  event.waitUntil(
    clients.openWindow('/') // Opens the root of your app.  Change if needed.
  );
});

// Optional: Add more sophisticated handling for different push event types
// or data payloads. 