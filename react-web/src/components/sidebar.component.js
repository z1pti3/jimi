import React from "react";

import './sidebar.component.css'

function Sidebar(props) {   
    return (
      <div id="sidebar">
        <h3>jimi</h3>
        <div id="navbar">
          <ul class="list-unstyled components">
              <p>Dummy Heading</p>
              <li>
                <button type="submit" className="btn btn-primary btn-block button">Home</button>
              </li>
              <li>
                <button type="submit" className="btn btn-primary btn-block button">Conducts</button>
              </li>
          </ul>
        </div>
      </div>
    );
  }
   
  export default Sidebar;