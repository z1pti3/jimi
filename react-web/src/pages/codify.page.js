import React, { Component } from "react";

import configData from "../config/config.json";
import { URL } from"./../utils/api";

import "./codify.page.css"

export default class CodifyPage extends Component {
    constructor(props) {
        super(props);
    }

    render() {
        return (
            <div className="pageContent0">
                <iframe className="codifyFrame" src={"codify/"}></iframe>
            </div>
        );
    }
}