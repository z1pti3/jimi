import React, { Component } from "react";

import { getSessionCSRF } from './../utils/session';

import configData from "./../config/config.json";

import { URL } from"./../utils/api";

import Table from "./../components/table.component"
import Loading from "./../components/loading.component"

import "./files.page.css"

export default class FilesPage extends Component {
    constructor(props) {
        super(props);
        this.state = {
            files: [],
            file: null,
            filename: null,
            loading : true
        }

        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        fetch(URL()+'storage/file/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            this.setState({ files : json["results"], loading : false });
        });

        this.change = this.change.bind(this);
        this.upload = this.upload.bind(this);
    }

    upload() {
        const formData = new FormData();
        formData.append('file', this.state.file);
        formData.append('CSRF', getSessionCSRF());
        const requestOptions = {
            method: 'PUT',
            credentials: 'include',
            body: formData,
        };
        fetch(URL()+'storage/file/'+this.state.filename+"/", requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            alert(JSON.stringify(json));
        });
    }

    changeFile = (event) => {
        this.setState({ file: event.target.files[0] });
	};

    change(event) {
        const target = event.target;
        var value = target.value;
        const name = target.name;
        if (target.type === 'checkbox') {
            if (target.checked) {
                this.state.hobbies[value] = value;   
            } else {
                this.state.hobbies.splice(value, 1);
            }
        } else {
            this.setState({ [name]: value });
        }   
    }

    render() {
        return !this.state.loading ? (
            <div className="pageContent1">
                <div>
                    <input type="text" name="filename" className="form-control textbox fileUploadFilename" placeholder="filename" onChange={this.change} />
                    <br/>
                    <input type="file" name="file" className="form-control textbox fileUploadFile" onChange={this.changeFile} />
                    <br/>
                    <button className="btn btn-primary btn-block button fileUpload" onClick={this.upload}>Upload</button>
                </div>
                <br/>
                Existing Files:
                <div>
                    <Table data={this.state.files} />
                </div>
            </div>
        ) : <Loading />
    }
}