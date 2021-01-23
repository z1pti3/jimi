import React, { Component } from "react";
import PropTypes from "prop-types";

import "./html.component.css"
import "./conductItem.component.css"



function ConductItem(props) {
    var d = new Date(0);
    d.setUTCSeconds(props.lastUpdateTime)
    return (
        <div className="conductItemContainer">
            <div className="conductItem">
                <div className="conductLeft">
                    <a className="conductTitle" href={"/conduct/?conductID="+props.id} title={props.name}>
                        {props.name}
                    </a>
                    <p className="conductState">
                        State: {props.state}
                    </p>
                </div>
                <div className="conductRight">
                    <p className="conductLastEdit">
                        Last Edit: {d.toLocaleString()}
                    </p>
                    <br/>
                    <div className="conductRightLinks">
                        <a className="conductDeleteLink" onClick={(e) => props.deleteConductClickHandler(e,props.id,props.name)}>
                            Delete
                        </a>
                        <p className="conductRightOptions">
                            /
                        </p>
                        <a className="conductEditLink" href={"/conductSettings/?conductID=" + props.id + "&edit=True"}>
                            Edit
                        </a>
                    </div>
                </div>
            </div>       
        </div>
    )
}

export default ConductItem;