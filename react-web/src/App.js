import React from 'react';
import {Container, Row, Col } from "react-bootstrap";

import Topbar from './components/topbar.component';
import Tab from './components/tab.component';
 
import './app.css';

function App() {
  return (
    <Container fluid>
      <Row>
        <Col>
        <Topbar />
        </Col>
      </Row>
      <Row>

        <Col id="pageContent-wrapper">
          <Tab />
          this is a test
        </Col> 
      </Row>
    </Container>
  );
}
 
export default App;