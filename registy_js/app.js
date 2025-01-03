const express = require('express');
const app = express();

// Middleware to parse form data (as POST requests often use this format)
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

let nodes = [];
let reputations = {};
let bizantines = [];

// Get reputations
app.get('/reputations', (req, res) => {
  res.json(reputations);
});

// Get nodes (filtered by bizantines)
app.get('/nodes', (req, res) => {
  const filteredNodes = nodes.filter(node => !bizantines.includes(node));
  res.json(filteredNodes);
});

// Get bizantines
app.get('/bizantines', (req, res) => {
  res.json(bizantines);
});

// Add a node
app.post('/node', (req, res) => {
  const { url } = req.body;

  if (bizantines.includes(url)) {
    bizantines = bizantines.filter(node => node !== url);
  }

  if (nodes.includes(url)) {
    return res.status(409).json({ node: url });
  }

  nodes.push(url);
  res.status(201).json(nodes);
});

// Remove a node
app.post('/rm_node', (req, res) => {
  const { url } = req.body;

  if (nodes.includes(url)) {
    nodes = nodes.filter(node => node !== url);
    return res.json({ node: url });
  }

  return res.status(409).json(nodes);
});

// Start the server
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
