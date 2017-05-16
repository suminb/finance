import { Component } from '@angular/core';
import { AppService } from './app.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  providers: [AppService]
})
export class AppComponent {
  title = 'app works!';
  body = 'This is a body';
  records = [];

  constructor(private appService: AppService) {
    this.records = appService.getRecords();
  }
}
